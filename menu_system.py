"""
menu_system.py - Ana Menu ve Ayarlar Ekrani
=============================================
Kamera varsa arka planda gosterir + el takibi. Yoksa siyah arka plan + mouse/klavye.
Ctrl+V ile yapistirma destegi.
"""

import cv2
import numpy as np
import time
from typing import Dict, Any, Optional, Tuple

from config_manager import (
    load_config, save_config, mask_api_key, AVAILABLE_MODELS, DEFAULT_CONFIG
)


def sanitize(text: str) -> str:
    tr = {"ş":"s","Ş":"S","ç":"c","Ç":"C","ğ":"g","Ğ":"G",
          "ı":"i","İ":"I","ö":"o","Ö":"O","ü":"u","Ü":"U"}
    for k, v in tr.items():
        text = text.replace(k, v)
    return text


def get_clipboard() -> str:
    """Pano icerigini dondurur.

    pyperclip cross-platform calisir ve PowerShell subprocess'inin aksine
    guvenlik yazilimlarini (Kaspersky vb.) tetiklemez (S15/S22 fix — Asama 6.2).
    """
    try:
        import pyperclip
        return (pyperclip.paste() or "").strip()
    except Exception:
        return ""


class MenuSystem:
    WINDOW_NAME = "D&D Macera Oyunu"

    # Renkler (BGR)
    PANEL = (25, 28, 35)
    ACCENT = (80, 180, 255)
    BTN = (40, 55, 75)
    BTN_H = (55, 80, 110)
    BTN_D = (50, 50, 160)
    BTN_DH = (70, 70, 200)
    WHITE = (230, 230, 230)
    DIM = (130, 130, 130)
    GREEN = (100, 220, 120)
    RED = (100, 100, 255)
    INP_BG = (30, 35, 45)
    INP_ACT = (45, 55, 75)
    INP_BRD = (80, 90, 110)
    INP_BRD_A = (100, 180, 255)
    PROGRESS = (80, 220, 180)

    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_B = cv2.FONT_HERSHEY_DUPLEX
    DWELL = 2.0  # El ile secim suresi

    def __init__(self, camera_manager=None):
        """
        Args:
            camera_manager: Paylasilan CameraManager (S22 fix — Asama 6.3).
                Verilirse menu kendi kamerasini ACMAZ; yoneticiden alir ve
                cikarken KAPATMAZ (oyun ayni kamerayi kullanmaya devam eder).
        """
        self.config = load_config()
        self.state = "main"
        self.running = True
        self.result: Optional[str] = None
        self.mouse_pos = (0, 0)
        self.mouse_clicked = False
        self._active_field = ""
        self._input_buffer = ""
        self._cam_msg = ""
        self._cam_msg_t = 0.0
        self._status = ""
        self._status_t = 0.0
        self._buttons: Dict[str, Tuple[int, int, int, int]] = {}
        self._custom_model_mode = False

        # Kamera (opsiyonel arka plan) — paylasilan yonetici varsa oradan
        self._cam_mgr = camera_manager
        self._cap = None
        self._cam_ok = False
        self._cam_w = 1280
        self._cam_h = 720
        self._try_camera()

        # El takibi icin dwell
        self._hover_btn = ""
        self._hover_start = 0.0

    def _try_camera(self):
        idx = self.config.get("camera_index", 0)

        # Paylasilan kamera yoneticisi varsa oradan al (yeniden acilmaz)
        if self._cam_mgr is not None:
            cap = self._cam_mgr.get(idx)
            if cap is not None:
                self._cam_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self._cam_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self._cap = cap
                self._cam_ok = True
            else:
                self._cap = None
                self._cam_ok = False
            return

        # Eski davranis: kendi kamerasini ac
        try:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self._cam_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self._cam_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self._cap = cap
                self._cam_ok = True
            else:
                cap.release()
        except Exception:
            pass

    def _read_bg(self) -> np.ndarray:
        if self._cam_ok and self._cap is not None:
            ret, frame = self._cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                # Koyulastir (overlay icin)
                dark = np.full_like(frame, (15, 15, 20))
                return cv2.addWeighted(frame, 0.25, dark, 0.75, 0)
        return np.full((self._cam_h, self._cam_w, 3), (15, 15, 20), dtype=np.uint8)

    # ------------------------------------------------------------------ #
    #  ANA DONGU                                                           #
    # ------------------------------------------------------------------ #

    def run(self) -> Dict[str, Any]:
        w, h = self._cam_w, self._cam_h
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.WINDOW_NAME, min(w, 1280), min(h, 720))
        cv2.setMouseCallback(self.WINDOW_NAME, self._mouse_cb)

        while self.running:
            frame = self._read_bg()
            self._buttons.clear()

            if self.state == "main":
                self._draw_main(frame)
            else:
                self._draw_settings(frame)

            cv2.imshow(self.WINDOW_NAME, frame)
            key = cv2.waitKey(30) & 0xFF
            self._handle_key(key)

            if self.mouse_clicked:
                self._handle_click()
                self.mouse_clicked = False

            if self.result is not None:
                break

        # Paylasilan kamera KAPATILMAZ — oyun kullanmaya devam edecek (S22).
        # Sadece menunun kendi actigi kamera kapatilir.
        if self._cam_mgr is None and self._cap is not None:
            self._cap.release()
        cv2.destroyWindow(self.WINDOW_NAME)
        cv2.waitKey(1)

        self.config["_action"] = self.result or "exit"
        return self.config

    # ------------------------------------------------------------------ #
    #  MOUSE                                                               #
    # ------------------------------------------------------------------ #

    def _mouse_cb(self, event, x, y, flags, param):
        self.mouse_pos = (x, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_clicked = True

    def _hover(self, name: str) -> bool:
        if name not in self._buttons:
            return False
        x1, y1, x2, y2 = self._buttons[name]
        mx, my = self.mouse_pos
        return x1 <= mx <= x2 and y1 <= my <= y2

    def _handle_click(self):
        if self.state == "main":
            if self._hover("start"):
                if not self.config.get("api_key"):
                    self._status = "Hata: Ayarlar'dan API anahtari girin!"
                    self._status_t = time.time()
                else:
                    self.result = "start"
            elif self._hover("settings"):
                self.state = "settings"
                self._active_field = ""
            elif self._hover("exit"):
                self.result = "exit"

        elif self.state == "settings":
            self._commit_field()
            if self._hover("back"):
                save_config(self.config)
                self.state = "main"
            elif self._hover("m_prev"):
                self._cycle_model(-1)
            elif self._hover("m_next"):
                self._cycle_model(1)
            elif self._hover("f_api"):
                self._active_field = "api_key"
                self._input_buffer = self.config.get("api_key", "")
            elif self._hover("f_tok"):
                self._active_field = "max_tokens"
                self._input_buffer = str(self.config.get("max_tokens", 1024))
            elif self._hover("f_cam"):
                self._active_field = "camera_index"
                self._input_buffer = str(self.config.get("camera_index", 0))
            elif self._hover("cam_test"):
                self._test_camera()
            elif self._hover("save"):
                save_config(self.config)
                self._status = "Ayarlar kaydedildi!"
                self._status_t = time.time()
            elif self._hover("f_model_custom"):
                self._active_field = "model_custom"
                self._input_buffer = self.config.get("model_name", "")

    # ------------------------------------------------------------------ #
    #  KLAVYE                                                              #
    # ------------------------------------------------------------------ #

    def _handle_key(self, key: int):
        if key == 255:
            return
        if key == 27:  # ESC
            if self.state == "settings":
                self._commit_field()
                save_config(self.config)
                self.state = "main"
                self._active_field = ""
            else:
                self.result = "exit"
            return

        # Ctrl+V paste (Windows: key 22)
        if key == 22 and self._active_field:
            clip = get_clipboard()
            if clip:
                self._input_buffer += clip
            return

        if self._active_field:
            if key == 13:  # Enter
                self._commit_field()
            elif key == 8:  # Backspace
                self._input_buffer = self._input_buffer[:-1]
            elif key == 9:  # Tab
                self._commit_field()
                fields = ["api_key", "max_tokens", "camera_index"]
                try:
                    idx = fields.index(self._active_field)
                    nf = fields[(idx + 1) % len(fields)]
                except ValueError:
                    nf = "api_key"
                self._active_field = nf
                if nf == "api_key":
                    self._input_buffer = self.config.get("api_key", "")
                elif nf == "max_tokens":
                    self._input_buffer = str(self.config.get("max_tokens", 1024))
                elif nf == "camera_index":
                    self._input_buffer = str(self.config.get("camera_index", 0))
            elif 32 <= key <= 126:
                self._input_buffer += chr(key)
            return

        if self.state == "main":
            if key == ord("1"):
                if not self.config.get("api_key"):
                    self._status = "Hata: Ayarlar'dan API anahtari girin!"
                    self._status_t = time.time()
                else:
                    self.result = "start"
            elif key == ord("2"):
                self.state = "settings"
            elif key == ord("3") or key == ord("q"):
                self.result = "exit"

    # ------------------------------------------------------------------ #
    #  ANA MENU CIZIMI                                                     #
    # ------------------------------------------------------------------ #

    def _draw_main(self, frame: np.ndarray):
        h, w = frame.shape[:2]
        cx = w // 2

        # Panel
        pw, ph = min(500, w - 60), 420
        px = cx - pw // 2
        py = (h - ph) // 2
        self._draw_panel(frame, px, py, pw, ph)

        # Baslik
        self._center_text(frame, "DUNGEONS & DRAGONS", cx, py + 55,
                          self.FONT_B, 1.3, self.ACCENT, 3)
        self._center_text(frame, "Webcam Kontrollu Rol Yapma Oyunu", cx, py + 90,
                          self.FONT, 0.6, self.DIM, 1)

        # Durum bilgileri - ayri satirlarda
        model = self.config.get("model_name", "?")
        has_key = bool(self.config.get("api_key"))
        self._center_text(frame, f"Model: {model}", cx, py + 125,
                          self.FONT, 0.5, self.DIM, 1)
        key_txt = "API: Tanimli" if has_key else "API: TANIMSIZ"
        key_c = self.GREEN if has_key else self.RED
        self._center_text(frame, sanitize(key_txt), cx, py + 150,
                          self.FONT, 0.5, key_c, 1)

        # Butonlar
        bw, bh = min(340, pw - 40), 60
        bx = cx - bw // 2

        self._draw_btn(frame, "start", bx, py + 180, bw, bh,
                       "[1] OYUNA BASLA", self.BTN, self.BTN_H)
        self._draw_btn(frame, "settings", bx, py + 255, bw, bh,
                       "[2] AYARLAR", self.BTN, self.BTN_H)
        self._draw_btn(frame, "exit", bx, py + 330, bw, bh,
                       "[3] CIKIS", self.BTN_D, self.BTN_DH)

        # Status
        if self._status and time.time() - self._status_t < 3:
            c = self.RED if "Hata" in self._status else self.GREEN
            self._center_text(frame, sanitize(self._status), cx, h - 30,
                              self.FONT, 0.55, c, 1)

    # ------------------------------------------------------------------ #
    #  AYARLAR CIZIMI                                                      #
    # ------------------------------------------------------------------ #

    def _draw_settings(self, frame: np.ndarray):
        h, w = frame.shape[:2]
        cx = w // 2

        pw, ph = min(720, w - 40), min(560, h - 40)
        px = cx - pw // 2
        py = (h - ph) // 2
        self._draw_panel(frame, px, py, pw, ph)

        self._center_text(frame, "AYARLAR", cx, py + 45,
                          self.FONT_B, 1.2, self.ACCENT, 3)

        left = px + 25
        right = px + pw - 25
        field_left = left + 150
        field_w = right - field_left

        # ---- AI Modeli ----
        ry = py + 85
        cv2.putText(frame, "AI Modeli:", (left, ry),
                    self.FONT, 0.6, self.WHITE, 1, cv2.LINE_AA)

        model = self.config.get("model_name", DEFAULT_CONFIG["model_name"])
        is_custom = model not in AVAILABLE_MODELS or model == "Ozel..."

        # Ok butonlari + model adi
        self._draw_btn(frame, "m_prev", field_left, ry - 22, 35, 30, "<",
                       self.BTN, self.BTN_H, 0.6)
        self._draw_btn(frame, "m_next", right - 35, ry - 22, 35, 30, ">",
                       self.BTN, self.BTN_H, 0.6)

        model_display = model if not is_custom else f"Ozel: {model}"
        self._center_text(frame, model_display, (field_left + 40 + right - 35) // 2,
                          ry, self.FONT, 0.55, self.ACCENT, 1)

        # Ozel model input (model "Ozel..." seciliyse veya aktif alan model_custom ise)
        if is_custom or self._active_field == "model_custom":
            ry2 = ry + 35
            cv2.putText(frame, "Model Adi:", (left, ry2),
                        self.FONT, 0.5, self.DIM, 1, cv2.LINE_AA)
            if self._active_field == "model_custom":
                dtxt = self._input_buffer + "|"
            else:
                dtxt = model
            self._draw_input(frame, "f_model_custom", field_left, ry2 - 18,
                             field_w, 30, dtxt, self._active_field == "model_custom")
            ry += 40  # Sonraki satirlari kaydir

        # ---- API Key ----
        ry += 55
        cv2.putText(frame, "API Key:", (left, ry),
                    self.FONT, 0.6, self.WHITE, 1, cv2.LINE_AA)
        api = self.config.get("api_key", "")
        if self._active_field == "api_key":
            dtxt = self._input_buffer + "|"
        else:
            dtxt = mask_api_key(api) if api else "(Ctrl+V ile yapistiriniz)"
        self._draw_input(frame, "f_api", field_left, ry - 18, field_w, 30,
                         dtxt, self._active_field == "api_key")

        # Paste bilgisi
        if self._active_field == "api_key":
            cv2.putText(frame, "Ctrl+V = Yapistir | Enter = Onayla",
                        (field_left, ry + 18), self.FONT, 0.4, self.DIM, 1, cv2.LINE_AA)

        # ---- Max Tokens ----
        ry += 60
        cv2.putText(frame, "Max Token:", (left, ry),
                    self.FONT, 0.6, self.WHITE, 1, cv2.LINE_AA)
        mtok = self.config.get("max_tokens", 1024)
        if self._active_field == "max_tokens":
            dtxt = self._input_buffer + "|"
        else:
            dtxt = str(mtok)
        self._draw_input(frame, "f_tok", field_left, ry - 18, 130, 30,
                         dtxt, self._active_field == "max_tokens")
        cv2.putText(frame, "(256-32000)", (field_left + 145, ry),
                    self.FONT, 0.4, self.DIM, 1, cv2.LINE_AA)

        # ---- Kamera ----
        ry += 60
        cv2.putText(frame, "Kamera ID:", (left, ry),
                    self.FONT, 0.6, self.WHITE, 1, cv2.LINE_AA)
        cidx = self.config.get("camera_index", 0)
        if self._active_field == "camera_index":
            dtxt = self._input_buffer + "|"
        else:
            dtxt = str(cidx)
        self._draw_input(frame, "f_cam", field_left, ry - 18, 70, 30,
                         dtxt, self._active_field == "camera_index")
        self._draw_btn(frame, "cam_test", field_left + 85, ry - 18, 130, 30,
                       "Test Et", self.BTN, self.BTN_H, 0.5)

        # Kamera test sonucu
        if self._cam_msg and time.time() - self._cam_msg_t < 4:
            c = self.GREEN if "Basarili" in self._cam_msg else self.RED
            cv2.putText(frame, sanitize(self._cam_msg), (field_left + 225, ry),
                        self.FONT, 0.45, c, 1, cv2.LINE_AA)

        # ---- Bilgi kutusu ----
        ry += 50
        info_lines = [
            "Gemini: Google AI Studio'dan API key alin.",
            "OpenAI: platform.openai.com | Claude: console.anthropic.com",
            "Alana tiklayin, Ctrl+V ile yapistiriniz. Tab ile gecis yapin.",
        ]
        for i, ln in enumerate(info_lines):
            cv2.putText(frame, sanitize(ln), (left + 5, ry + i * 20),
                        self.FONT, 0.4, self.DIM, 1, cv2.LINE_AA)

        # ---- Alt butonlar ----
        btn_y = py + ph - 60
        self._draw_btn(frame, "save", left, btn_y, 140, 40,
                       "KAYDET", (40, 100, 60), (50, 140, 80), 0.65)
        self._draw_btn(frame, "back", right - 140, btn_y, 140, 40,
                       "GERI (ESC)", self.BTN, self.BTN_H, 0.55)

        # Status
        if self._status and time.time() - self._status_t < 3:
            c = self.RED if "Hata" in self._status else self.GREEN
            self._center_text(frame, sanitize(self._status), cx, btn_y + 55,
                              self.FONT, 0.55, c, 1)

    # ------------------------------------------------------------------ #
    #  CIZIM YARDIMCILARI                                                  #
    # ------------------------------------------------------------------ #

    def _draw_panel(self, frame, x, y, w, h):
        ov = frame.copy()
        cv2.rectangle(ov, (x, y), (x + w, y + h), self.PANEL, -1)
        cv2.addWeighted(ov, 0.75, frame, 0.25, 0, frame)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 55, 65), 2)

    def _draw_btn(self, frame, name, x, y, w, h, text,
                  color, hcolor, fs=0.7):
        self._buttons[name] = (x, y, x + w, y + h)
        hov = self._hover(name)
        bg = hcolor if hov else color
        ov = frame.copy()
        cv2.rectangle(ov, (x, y), (x + w, y + h), bg, -1)
        cv2.addWeighted(ov, 0.8, frame, 0.2, 0, frame)
        bc = self.ACCENT if hov else (60, 65, 80)
        cv2.rectangle(frame, (x, y), (x + w, y + h), bc, 2 if hov else 1)
        (tw, th), _ = cv2.getTextSize(text, self.FONT, fs, 2)
        cv2.putText(frame, text, (x + (w - tw) // 2, y + (h + th) // 2),
                    self.FONT, fs, self.WHITE, 2, cv2.LINE_AA)

    def _draw_input(self, frame, name, x, y, w, h, text, active):
        self._buttons[name] = (x, y, x + w, y + h)
        bg = self.INP_ACT if active else self.INP_BG
        bd = self.INP_BRD_A if active else self.INP_BRD
        cv2.rectangle(frame, (x, y), (x + w, y + h), bg, -1)
        cv2.rectangle(frame, (x, y), (x + w, y + h), bd, 1)
        maxc = max(5, (w - 12) // 8)
        d = text if len(text) <= maxc else "..." + text[-(maxc - 3):]
        cv2.putText(frame, d, (x + 6, y + h - 8),
                    self.FONT, 0.45, self.WHITE, 1, cv2.LINE_AA)

    def _center_text(self, frame, text, cx, y, font, fs, color, thick):
        (tw, _), _ = cv2.getTextSize(text, font, fs, thick)
        cv2.putText(frame, text, (cx - tw // 2, y), font, fs, color, thick, cv2.LINE_AA)

    # ------------------------------------------------------------------ #
    #  ISLEVLER                                                            #
    # ------------------------------------------------------------------ #

    def _cycle_model(self, d):
        cur = self.config.get("model_name", DEFAULT_CONFIG["model_name"])
        try:
            idx = AVAILABLE_MODELS.index(cur)
        except ValueError:
            idx = 0
        idx = (idx + d) % len(AVAILABLE_MODELS)
        sel = AVAILABLE_MODELS[idx]
        if sel == "Ozel...":
            self._active_field = "model_custom"
            self._input_buffer = self.config.get("model_name", "")
        else:
            self.config["model_name"] = sel

    def _commit_field(self):
        if not self._active_field:
            return
        if self._active_field == "api_key":
            self.config["api_key"] = self._input_buffer.strip()
        elif self._active_field == "max_tokens":
            try:
                self.config["max_tokens"] = max(256, min(32000, int(self._input_buffer.strip())))
            except ValueError:
                pass
        elif self._active_field == "camera_index":
            try:
                self.config["camera_index"] = max(0, min(10, int(self._input_buffer.strip())))
            except ValueError:
                pass
        elif self._active_field == "model_custom":
            val = self._input_buffer.strip()
            if val:
                self.config["model_name"] = val
        self._active_field = ""
        self._input_buffer = ""

    def _test_camera(self):
        idx = self.config.get("camera_index", 0)

        # Paylasilan yonetici varsa: ayni index zaten acikken yeniden ACMADAN
        # test edilir (Kaspersky bildirimi tetiklenmez) — S22 fix.
        if self._cam_mgr is not None:
            ok, msg = self._cam_mgr.test(idx)
            self._cam_msg = msg
            self._cam_msg_t = time.time()
            self._try_camera()  # Menu arka planini guncel kameraya bagla
            return

        # Eski davranis: kapat, test et, yeniden ac
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            self._cam_ok = False
        try:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                self._cam_msg = f"Basarili! Kamera {idx} calisiyor." if ret else f"Hata: Kamera {idx} goruntu vermiyor."
            else:
                self._cam_msg = f"Hata: Kamera {idx} acilamadi."
        except Exception as e:
            self._cam_msg = f"Hata: {e}"
        self._cam_msg_t = time.time()
        # Menu kamerasini yeniden ac
        self._try_camera()
