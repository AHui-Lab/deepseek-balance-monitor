# -*- coding: utf-8 -*-
import tkinter as tk, json, os, threading, math, subprocess, sys
import requests
try:
    from deepseek_tracker import get_today_stats
except ImportError:
    def get_today_stats(): return None

BASE = os.path.dirname(os.path.abspath(__file__))
CFG  = os.path.join(BASE, "deepseek_config.json")
USAGE_FILE = os.path.join(BASE, "deepseek_usage.json")
UPDATE_SCRIPT = os.path.join(BASE, "update_data.py")
URL  = "https://api.deepseek.com/user/balance"
REFRESH = 60
MONTHLY_REFRESH = 10 * 60
WW, HC, HE = 300, 36, 350

BG  = "#0a0a14"
SF  = "#121228"
BL  = "#7aa2f7"
GN  = "#9ece6a"
YW  = "#e0af68"
RD  = "#f7768e"
TX  = "#e2e2f0"
SB  = "#8888aa"
BD  = "rgba(255,255,255,0.06)"

RING_R  = 46
RING_CX = 150
RING_CY = 80


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DeepSeek")
        self.attributes("-topmost", True)
        self.configure(bg=BG)
        self.resizable(False, False)
        self._c = False; self._monthly_open = False
        self._dx = 0
        self._dy = 0
        self._key = ""
        self._model = "deepseek-chat"
        self._monthly_refreshing = False
        self._load()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        m = 20
        self.geometry(f"{WW}x{HE}+{sw-WW-m}+{sh-HE-m-48}")
        self._ui()
        self._ev()
        threading.Thread(target=self._fr, daemon=True).start()
        self.after(REFRESH * 1000, self._ar)
        self.after(3000, self._refresh_monthly)
        self.after(MONTHLY_REFRESH * 1000, self._ar_monthly)

    def _load(self):
        try:
            self._key = os.getenv("DEEPSEEK_API_KEY", "").strip()
            self._model = os.getenv("DEEPSEEK_MODEL", self._model).strip() or self._model
            if os.path.exists(CFG):
                with open(CFG, "r", encoding="utf-8-sig") as f:
                    cfg = json.load(f)
                    self._key = self._key or cfg.get("api_key", "").strip()
                    self._model = cfg.get("model", self._model)
        except:
            pass

    def _ui(self):
        # Main container with rounded-rect via canvas
        self.cv_main = tk.Canvas(self, bg=BG, highlightthickness=0, width=WW, height=HE)
        self.cv_main.pack(fill=tk.BOTH, expand=True)

        # Card background
        self._card_id = self.cv_main.create_rectangle(
            6, 6, WW-6, HE-6, fill=SF, outline="", width=0
        )
        # Top accent line
        self._accent_id = self.cv_main.create_line(
            6, 6, WW-6, 6, fill=BL, width=2
        )

        # Header
        self._header_id = self.cv_main.create_text(
            20, 22, text="DeepSeek v4", fill=BL,
            font=("Segoe UI", 11, "bold"), anchor="w"
        )
        self._dot_id = self.cv_main.create_oval(
            WW-30, 16, WW-18, 28, fill=SB, outline=""
        )
        self._toggle_id = self.cv_main.create_text(
            WW-38, 22, text="-", fill=SB,
            font=("Segoe UI", 11), anchor="e"
        )
        # Refresh button
        rx1, rx2 = WW-88, WW-42
        self._rf_bg = self.cv_main.create_rectangle(
            rx1, 12, rx2, 29, fill="#263b70", outline=BL, width=1
        )
        self._rf_id = self.cv_main.create_text(
            (rx1+rx2)//2, 20, text="REFRESH", fill=TX,
            font=("Segoe UI", 8, "bold")
        )
        self.cv_main.tag_bind(self._rf_bg, "<Button-1>",
            lambda e: threading.Thread(target=self._fr, daemon=True).start())
        self.cv_main.tag_bind(self._rf_id, "<Button-1>",
            lambda e: threading.Thread(target=self._fr, daemon=True).start())

        # Ring background
        self._ring_bg_id = self.cv_main.create_arc(
            RING_CX-RING_R, RING_CY-RING_R, RING_CX+RING_R, RING_CY+RING_R,
            outline=SB, width=4, style="arc", start=90, extent=-359
        )
        # Ring foreground (drawn as arc)
        self._ring_fg_id = None

        # Balance number
        self._bal_id = self.cv_main.create_text(
            RING_CX, RING_CY-2, text="...", fill=TX,
            font=("Segoe UI", 30, "bold"), anchor="center"
        )
        # Currency label below number
        self._cur_id = self.cv_main.create_text(
            RING_CX, RING_CY+22, text="", fill=SB,
            font=("Segoe UI", 11), anchor="center"
        )

        # Info text
        self._info_id = self.cv_main.create_text(
            RING_CX, RING_CY+RING_R+20, text="Connecting...", fill=SB,
            font=("Segoe UI", 10), anchor="center"
        )

        # Monthly section toggle button (below info)




        # Split bars section
        bar_y = RING_CY+RING_R+44
        self._gift_label_id = self.cv_main.create_text(
            20, bar_y, text="GIFT", fill=SB,
            font=("Segoe UI", 8, "bold"), anchor="w"
        )
        self._bar_g = self.cv_main.create_rectangle(
            80, bar_y-4, 80, bar_y+4, fill=BL, outline=""
        )
        self._val_g_id = self.cv_main.create_text(
            WW-16, bar_y, text="--", fill=TX,
            font=("Segoe UI", 9, "bold"), anchor="e"
        )

        bar_y2 = bar_y + 24
        self._topped_label_id = self.cv_main.create_text(
            20, bar_y2, text="TOPPED", fill=SB,
            font=("Segoe UI", 8, "bold"), anchor="w"
        )
        self._bar_tp = self.cv_main.create_rectangle(
            80, bar_y2-4, 80, bar_y2+4, fill="#7dcfff", outline=""
        )
        self._val_tp_id = self.cv_main.create_text(
            WW-16, bar_y2, text="--", fill=TX,
            font=("Segoe UI", 9, "bold"), anchor="e"
        )

        # Monthly section toggle button (below split bars)
        self._monthly_btn = self.cv_main.create_text(
            RING_CX, bar_y2+25, text="MONTHLY USAGE  +", fill=BL,
            font=("Segoe UI", 8, "bold")
        )
        self.cv_main.tag_bind(self._monthly_btn, "<Button-1>",
            lambda e: self._tg_monthly())

        # --- Usage stats section (below split bars) ---
        us_y = bar_y2 + 43
        self._us_div = self.cv_main.create_line(
            20, us_y-7, WW-20, us_y-7, fill="#242443", width=1,
            state="hidden"
        )

        # Monthly refresh button
        mrf_y = us_y + 5
        self._mrf_bg = self.cv_main.create_rectangle(
            WW-78, mrf_y-8, WW-20, mrf_y+8,
            fill="#20203a", outline="#45456d", width=1, state="hidden"
        )
        self._mrf_id = self.cv_main.create_text(
            WW-49, mrf_y, text="REFRESH", fill=TX,
            font=("Segoe UI", 8, "bold"), state="hidden"
        )
        self.cv_main.tag_bind(self._mrf_bg, "<Button-1>",
            lambda e: self._refresh_monthly())
        self.cv_main.tag_bind(self._mrf_id, "<Button-1>",
            lambda e: self._refresh_monthly())
        self._us_title = self.cv_main.create_text(
            22, us_y+5, text="This month / v4-pro", fill=SB,
            font=("Segoe UI", 8, "bold"), anchor="w", state="hidden"
        )
        # Token count
        self._us_tokens = self.cv_main.create_text(
            22, us_y+29, text="", fill=TX,
            font=("Segoe UI", 12, "bold"), anchor="w", state="hidden"
        )
        # Hit rate + cost on same line
        self._us_hr = self.cv_main.create_text(
            22, us_y+51, text="", fill=SB,
            font=("Segoe UI", 9), anchor="w", state="hidden"
        )
        self._us_cost = self.cv_main.create_text(
            WW-22, us_y+51, text="", fill=TX,
            font=("Segoe UI", 9, "bold"), anchor="e", state="hidden"
        )

        # Footer timestamp
        self._ft_id = self.cv_main.create_text(
            RING_CX, HE-14, text="", fill=SB,
            font=("Segoe UI", 8), anchor="center"
        )

        # Collapsed view elements (hidden initially)
        self._col_bal_id = self.cv_main.create_text(
            WW//2, HC//2, text="", fill=TX,
            font=("Segoe UI", 12, "bold"), anchor="center", state="hidden"
        )
        self._col_dot_id = self.cv_main.create_arc(
            WW-18, HC//2-5, WW-6, HC//2+7, fill=SB, outline="", state="hidden"
        )

        # State tracking
        self._state = ""

    def _ev(self):
        self.cv_main.bind("<Button-1>", self._ds)
        self.cv_main.bind("<B1-Motion>", self._dm)
        self.cv_main.bind("<Double-Button-1>", lambda e: self._tg())
        self.bind("<Button-3>", self._ctx)

    def _ds(self, e):
        self._dx = e.x_root - self.winfo_x()
        self._dy = e.y_root - self.winfo_y()

    def _dm(self, e):
        self.geometry(f"+{e.x_root-self._dx}+{e.y_root-self._dy}")

    def _tg(self):
        self._c = not self._c
        if self._c:
            self.geometry(f"{WW}x{HC}")
            # Hide main elements
            for id_ in [self._card_id, self._accent_id, self._dot_id,
                         self._ring_bg_id,
                         self._header_id, self._bal_id, self._cur_id, self._info_id,
                         self._gift_label_id, self._topped_label_id,
                         self._bar_g, self._bar_tp, self._val_g_id,
                         self._val_tp_id, self._monthly_btn, self._ft_id,
                         self._us_div, self._mrf_bg, self._mrf_id,
                         self._us_title, self._us_tokens,
                         self._us_hr, self._us_cost,
                         self._rf_bg, self._rf_id]:
                self.cv_main.itemconfig(id_, state="hidden")
            if self._ring_fg_id:
                self.cv_main.itemconfig(self._ring_fg_id, state="hidden")
            # Show collapsed
            self.cv_main.itemconfig(self._col_bal_id, state="normal")
            self.cv_main.itemconfig(self._col_dot_id, state="normal")
            self.cv_main.itemconfig(self._toggle_id, text="+")
        else:
            self.geometry(f"{WW}x{HE}")
            self.cv_main.itemconfig(self._col_bal_id, state="hidden")
            self.cv_main.itemconfig(self._col_dot_id, state="hidden")
            for id_ in [self._card_id, self._accent_id, self._dot_id,
                         self._ring_bg_id,
                         self._header_id, self._bal_id, self._cur_id, self._info_id,
                         self._gift_label_id, self._topped_label_id,
                         self._bar_g, self._bar_tp, self._val_g_id,
                         self._val_tp_id, self._monthly_btn, self._ft_id,
                         self._rf_bg, self._rf_id]:
                self.cv_main.itemconfig(id_, state="normal")
            monthly_state = "normal" if self._monthly_open else "hidden"
            for id_ in [self._us_div, self._mrf_bg, self._mrf_id,
                        self._us_title, self._us_tokens,
                        self._us_hr, self._us_cost]:
                self.cv_main.itemconfig(id_, state=monthly_state)
            if self._ring_fg_id:
                self.cv_main.itemconfig(self._ring_fg_id, state="normal")
            self.cv_main.itemconfig(self._toggle_id, text="-")

    def _ctx(self, e):
        m = tk.Menu(self, tearoff=0, bg=SF, fg=TX, activebackground=BL,
                     activeforeground=BG, font=("Segoe UI", 9))
        m.add_command(label="Refresh",
                       command=lambda: threading.Thread(target=self._fr, daemon=True).start())
        m.add_separator()
        m.add_command(label="Exit", command=self.destroy)
        m.post(e.x_root, e.y_root)

    def _fr(self):
        data, err = {}, None
        try:
            if not self._key:
                err = "No API key"
            else:
                r = requests.get(URL,
                    headers={"Authorization": f"Bearer {self._key}"},
                    timeout=10)
                if r.status_code == 200:
                    data = r.json()
                else:
                    err = f"HTTP {r.status_code}: {r.text[:80]}"
        except requests.ConnectionError:
            err = "Network error"
        except requests.Timeout:
            err = "Timed out"
        except Exception as ex:
            err = str(ex)[:80]
        self.after(0, self._up, data, err)

    def _up(self, data, err):
        if err:
            self._set_state("error")
            self.cv_main.itemconfig(self._bal_id, text="Error", fill=RD)
            self.cv_main.itemconfig(self._cur_id, text="")
            self.cv_main.itemconfig(self._info_id, text=err, fill=RD)
            self.cv_main.coords(self._bar_g, 80, 0, 80, 0)
            self.cv_main.coords(self._bar_tp, 80, 0, 80, 0)
            self.cv_main.itemconfig(self._val_g_id, text="--")
            self.cv_main.itemconfig(self._val_tp_id, text="--")
            self._ring(0)
            self.cv_main.itemconfig(self._col_bal_id, text="Error", fill=RD)
        elif data.get("is_available"):
            bs = data.get("balance_infos", [])
            if bs:
                b = bs[0]
                t = float(b.get("total_balance", 0))
                g = float(b.get("granted_balance", 0))
                tp = float(b.get("topped_up_balance", 0))
                cur = b.get("currency", "CNY")
                m = max(g, tp, t, 1)
                ring_pct = min(1.0, t / m)
                state = "ok" if t > 1 else "warn"
                self._set_state(state)
                color = GN if t > 1 else YW
                self.cv_main.itemconfig(self._bal_id, text=f"{t:.2f}", fill=color)
                self.cv_main.itemconfig(self._cur_id, text=cur, fill=SB)
                self.cv_main.itemconfig(self._info_id, text=f"Balance OK | {self._model}", fill=SB)
                # Bars
                gpct = g / m
                tppct = tp / m
                bar_max = WW - 100
                self.cv_main.coords(self._bar_g, 80, RING_CY+RING_R+44-4,
                                    80 + gpct * bar_max, RING_CY+RING_R+44+4)
                self.cv_main.coords(self._bar_tp, 80, RING_CY+RING_R+68-4,
                                    80 + tppct * bar_max, RING_CY+RING_R+68+4)
                self.cv_main.itemconfig(self._val_g_id, text=f"{cur} {g:.2f}")
                self.cv_main.itemconfig(self._val_tp_id, text=f"{cur} {tp:.2f}")
                self._ring(ring_pct)
                self.cv_main.itemconfig(self._col_bal_id, text=f"{cur} {t:.2f}", fill=color)
            else:
                self._set_state("warn")
                self.cv_main.itemconfig(self._bal_id, text="N/A", fill=YW)
                self.cv_main.itemconfig(self._cur_id, text="")
                self.cv_main.itemconfig(self._info_id, text="No balance info", fill=YW)
                self.cv_main.coords(self._bar_g, 80, 0, 80, 0)
                self.cv_main.coords(self._bar_tp, 80, 0, 80, 0)
                self.cv_main.itemconfig(self._val_g_id, text="--")
                self.cv_main.itemconfig(self._val_tp_id, text="--")
                self._ring(0)
                self.cv_main.itemconfig(self._col_bal_id, text="N/A", fill=YW)
        else:
            self._set_state("warn")
            self.cv_main.itemconfig(self._bal_id, text="Unavail", fill=YW)
            self.cv_main.itemconfig(self._cur_id, text="")
            self.cv_main.itemconfig(self._info_id, text="is_available=false", fill=YW)
            self.cv_main.coords(self._bar_g, 80, 0, 80, 0)
            self.cv_main.coords(self._bar_tp, 80, 0, 80, 0)
            self.cv_main.itemconfig(self._val_g_id, text="--")
            self.cv_main.itemconfig(self._val_tp_id, text="--")
            self._ring(0)
            self.cv_main.itemconfig(self._col_bal_id, text="Unavail", fill=YW)

        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.cv_main.itemconfig(self._ft_id, text=f"Last: {ts}  |  Auto: {REFRESH}s")
        self._show_usage()

    def _set_state(self, s):
        self._state = s
        col = {"ok": GN, "warn": YW, "error": RD}.get(s, SB)
        self.cv_main.itemconfig(self._dot_id, fill=col)
        self.cv_main.itemconfig(self._col_dot_id, fill=col)

    def _ring(self, pct):
        if self._ring_fg_id:
            self.cv_main.delete(self._ring_fg_id)
        if pct <= 0:
            self._ring_fg_id = None
            return
        extent = -pct * 359.9
        color = GN if pct >= 0.5 else (YW if pct >= 0.1 else RD)
        self._ring_fg_id = self.cv_main.create_arc(
            RING_CX-RING_R, RING_CY-RING_R,
            RING_CX+RING_R, RING_CY+RING_R,
            outline=color, width=4, style="arc",
            start=90, extent=extent
        )

    def _show_usage(self):
        platform = self._fetch_platform()
        if platform:
            tk = platform["month_tokens"]
            cost = platform["month_cost"]
            reqs = platform["month_requests"]
            # Format as compact
            if tk >= 1_000_000:
                tks = f"{tk/1_000_000:.1f}M"
            else:
                tks = f"{tk:,}"
            self.cv_main.itemconfig(self._us_tokens,
                text=f"{tks} tokens", fill=TX)
            self.cv_main.itemconfig(self._us_hr,
                text=f"{reqs} requests", fill=SB)
            self.cv_main.itemconfig(
                self._us_cost, text=f"CNY {cost:.2f}", fill=TX
            )
            self._platform_ok = True
        else:
            self.cv_main.itemconfig(self._us_tokens,
                text="Run update_data.py", fill=YW)
            self.cv_main.itemconfig(self._us_hr,
                text="to refresh", fill=SB)
            self.cv_main.itemconfig(self._us_cost,
                text="monthly data", fill=SB)

    def _fetch_platform(self):
        try:
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not data:
                return None
            d = data[max(data)]
            reqs = d.get("month_requests", 0)
            tokens = d.get("month_tokens", 0)
            cost = d.get("month_cost", 0)
            if tokens == 0:
                return None
            return {"month_requests": reqs, "month_tokens": tokens, "month_cost": cost}
        except (OSError, ValueError, TypeError):
            return None

    def _tg_monthly(self):
        self._monthly_open = not self._monthly_open
        st = "normal" if self._monthly_open else "hidden"
        for item in [self._us_div, self._us_title, self._us_tokens,
                     self._us_hr, self._us_cost, self._mrf_bg, self._mrf_id]:
            self.cv_main.itemconfig(item, state=st)
        self.cv_main.itemconfig(self._monthly_btn,
            text="MONTHLY USAGE  +" if not self._monthly_open
            else "MONTHLY USAGE  -")
        if self._monthly_open:
            # Show monthly data when expanding
            self.after(200, self._show_usage)

    def _refresh_monthly(self):
        if self._monthly_refreshing:
            return
        self._monthly_refreshing = True
        self.cv_main.itemconfig(self._mrf_id, text="Updating")
        if self._monthly_open:
            self.cv_main.itemconfig(self._us_tokens, text="Refreshing...", fill=YW)
        threading.Thread(target=self._run_monthly_update, daemon=True).start()

    def _run_monthly_update(self):
        error = None
        try:
            result = subprocess.run(
                [sys.executable, UPDATE_SCRIPT],
                cwd=BASE,
                capture_output=True,
                text=True,
                timeout=45,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            output = (result.stderr or result.stdout or "").strip()
            if result.returncode != 0 or "ERROR:" in result.stdout:
                error = output or "Monthly update failed"
        except subprocess.TimeoutExpired:
            error = "Monthly update timed out"
        except Exception as ex:
            error = str(ex)
        self.after(0, self._monthly_update_done, error)

    def _monthly_update_done(self, error):
        self._monthly_refreshing = False
        self.cv_main.itemconfig(self._mrf_id, text="Refresh")
        self._show_usage()
        if error and self._monthly_open:
            self.cv_main.itemconfig(self._us_title, text=error[:42], fill=YW)
        else:
            self.cv_main.itemconfig(self._us_title, fill=SB)

    def _ar_monthly(self):
        self._refresh_monthly()
        self.after(MONTHLY_REFRESH * 1000, self._ar_monthly)

    def _ar(self):
        threading.Thread(target=self._fr, daemon=True).start()
        self.after(REFRESH * 1000, self._ar)


if __name__ == "__main__":
    App().mainloop()
