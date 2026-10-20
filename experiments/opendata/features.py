"""Content-blind keystroke and mouse window features (spec FR-02/FR-03).

Keys are reduced to hand/zone classes before any feature is computed, so the
same extractor works on Aalto (JS keycodes), CMU LASER-2012 (key names) and
Tappy (hand labels only). No key identity survives.
"""
import numpy as np

L, R, S, B, M, O = 0, 1, 2, 3, 4, 5      # left, right, space, backspace/delete, modifier, other
PAUSE_MS = 1500.0                        # PP gaps above this are pauses, not digraphs
TRANS = [(a, b) for a in (L, R, S) for b in (L, R, S) if not (a == S and b == S)]  # 8 transitions

_LEFT = set("qwertasdfgzxcvb12345`~!@#$%")
_RIGHT = set("yuiophjklnm67890-=[];',./\\^&*()_+{}:\"<>?|")


def cls_from_char(ch):
    c = ch.lower()
    if c == " ":
        return S
    if c in _LEFT:
        return L
    if c in _RIGHT:
        return R
    return O


def cls_from_jskeycode(kc):
    """JavaScript keyCode -> class (QWERTY assumption)."""
    kc = np.asarray(kc)
    out = np.full(kc.shape, O, dtype=np.int8)
    letters = "QWERTYUIOPASDFGHJKLZXCVBNM"
    left_letters = set("QWERTASDFGZXCVB")
    for ch in letters:
        out[kc == ord(ch)] = L if ch in left_letters else R
    for d in range(10):
        out[kc == 48 + d] = L if d in (1, 2, 3, 4, 5) else R
    out[kc == 32] = S
    out[(kc == 8) | (kc == 46)] = B
    out[(kc == 16) | (kc == 17) | (kc == 18) | (kc == 20) | (kc == 91) | (kc == 93)] = M
    out[(kc >= 186) & (kc <= 222)] = R      # ; = , - . / ` [ \ ] ' : mostly right hand (` is left, minor)
    out[kc == 192] = L
    return out


# ---------------------------------------------------------------- keystroke features
KEY_FEATURES = (
    [f"hold_mu_{n}" for n in "LRS"] + [f"hold_sd_{n}" for n in "LRS"] +
    [f"pp_mu_{'LRS'[a]}{'LRS'[b]}" for a, b in TRANS] +
    [f"pp_sd_{'LRS'[a]}{'LRS'[b]}" for a, b in TRANS] +
    [f"rp_mu_{'LRS'[a]}{'LRS'[b]}" for a, b in TRANS] +
    ["rollover_frac", "pp_median", "pause_frac", "burstiness"]
)
KEY_EXTRA = ["backspace_frac", "hold_mu_M"]           # not available in Tappy
N_KEY = len(KEY_FEATURES)


def _ms(x):
    return np.nanmean(x) if x.size else np.nan


def _sd(x):
    return np.nanstd(x) if x.size > 1 else np.nan


def key_window(press, release, cls, seg, extra=True):
    """Feature vector for one window of keystrokes (arrays sorted by press time).

    press/release in ms; cls in {L,R,S,B,M,O}; seg = continuity id (digraphs are
    only formed inside the same seg, e.g. same sentence / same typing burst file).
    Returns float32 vector (len N_KEY [+ 2]); NaN where a feature has no support.
    """
    hold = release - press
    ok = (hold > 0) & (hold < 2000)
    f = []
    for c in (L, R, S):
        f.append(_ms(hold[ok & (cls == c)]))
    for c in (L, R, S):
        f.append(_sd(hold[ok & (cls == c)]))
    same = seg[1:] == seg[:-1]
    pp = press[1:] - press[:-1]
    rp = press[1:] - release[:-1]
    a, b = cls[:-1], cls[1:]
    dig = same & (pp > 0) & (pp < PAUSE_MS)
    tmasks = [dig & (a == x) & (b == y) for x, y in TRANS]
    f += [_ms(pp[m]) for m in tmasks]
    f += [_sd(pp[m]) for m in tmasks]
    f += [_ms(rp[m]) for m in tmasks]
    d = pp[dig]
    f.append(np.mean(rp[dig] < 0) if d.size else np.nan)
    f.append(np.median(d) if d.size else np.nan)
    sp = same & (pp > 0)
    f.append(np.mean(pp[sp] >= PAUSE_MS) if sp.any() else np.nan)
    iat = pp[sp]
    if iat.size > 2:
        mu, sd = iat.mean(), iat.std()
        f.append((sd - mu) / (sd + mu) if sd + mu > 0 else np.nan)   # Goh-Barabasi burstiness
    else:
        f.append(np.nan)
    if extra:
        f.append(np.mean(cls == B))
        f.append(_ms(hold[ok & (cls == M)]))
    return np.asarray(f, dtype=np.float32)


def key_windows(press, release, cls, seg, n_keys=None, active_s=None, extra=True, min_keys=20):
    """Split a chronologically sorted keystroke stream into consecutive, non-overlapping
    windows of n_keys keystrokes, or of active_s seconds of *active* typing time
    (sum of PP gaps capped at PAUSE_MS within a seg). Returns (feats[n_win,F], start_ms[n_win])."""
    n = press.size
    if n < min_keys:
        return np.zeros((0, N_KEY + (2 if extra else 0)), np.float32), np.zeros(0)
    if n_keys:
        edges = list(range(0, n - n_keys + 1, n_keys))
        bounds = [(s, s + n_keys) for s in edges]
    else:
        gap = np.diff(press, prepend=press[0])
        gap[0] = 0
        newseg = np.r_[True, seg[1:] != seg[:-1]]
        gap = np.where(newseg, 0, np.minimum(gap, PAUSE_MS))
        act = np.cumsum(gap) / 1000.0
        win = np.floor(act / active_s).astype(int)
        bounds = []
        for w in range(win.max()):          # drop the last (incomplete) window
            idx = np.flatnonzero(win == w)
            if idx.size >= min_keys:
                bounds.append((idx[0], idx[-1] + 1))
    feats = [key_window(press[s:e], release[s:e], cls[s:e], seg[s:e], extra) for s, e in bounds]
    starts = [press[s] for s, _ in bounds]
    if not feats:
        return np.zeros((0, N_KEY + (2 if extra else 0)), np.float32), np.zeros(0)
    return np.vstack(feats), np.asarray(starts)


# ---------------------------------------------------------------- mouse features
MOUSE_FEATURES = [
    "v_mu", "v_sd", "a_mu", "a_sd", "jerk_mu", "angvel_mu", "angvel_sd", "curv_mu",
    "straight_mu", "straight_sd", "mvdur_mu", "mvlen_mu", "click_dwell_mu", "click_dwell_sd",
    "pause_frac", "dir_0", "dir_1", "dir_2", "dir_3", "dir_4", "dir_5", "dir_6", "dir_7",
]


def mouse_window(t, x, y, is_move, down, up):
    """t in seconds; is_move marks pointer-move samples; down/up are button event times
    (paired, same length). Movement segments split at gaps > 0.5 s or at clicks."""
    f = []
    tm, xm, ym = t[is_move], x[is_move], y[is_move]
    dt = np.diff(tm)
    dx, dy = np.diff(xm), np.diff(ym)
    ds = np.hypot(dx, dy)
    good = (dt > 1e-4) & (dt < 0.5)
    v = np.where(good, ds / np.where(good, dt, 1), np.nan)
    acc = np.diff(v) / np.where(dt[1:] > 1e-4, dt[1:], np.nan)
    jerk = np.diff(acc) / np.where(dt[2:] > 1e-4, dt[2:], np.nan)
    ang = np.arctan2(dy, dx)
    dang = np.angle(np.exp(1j * np.diff(ang)))
    angvel = dang / np.where(dt[1:] > 1e-4, dt[1:], np.nan)
    curv = np.abs(dang) / np.where(ds[1:] > 0, ds[1:], np.nan)
    def m(z): return np.nanmean(z) if np.isfinite(z).any() else np.nan
    def s(z): return np.nanstd(z) if np.isfinite(z).sum() > 1 else np.nan
    va = np.abs(acc)
    f += [m(v), s(v), m(va), s(va), m(np.abs(jerk)), m(np.abs(angvel)), s(angvel), m(curv)]
    # movement segments
    br = np.r_[0, np.flatnonzero(~good) + 1, tm.size]
    st, dur, ln = [], [], []
    for i in range(len(br) - 1):
        a, b = br[i], br[i + 1]
        if b - a >= 4:
            path = np.hypot(np.diff(xm[a:b]), np.diff(ym[a:b])).sum()
            disp = np.hypot(xm[b - 1] - xm[a], ym[b - 1] - ym[a])
            if path > 5:
                st.append(disp / path); dur.append(tm[b - 1] - tm[a]); ln.append(path)
    st = np.asarray(st)
    f += [m(st), s(st), m(np.asarray(dur)), m(np.log1p(np.asarray(ln)))]
    dw = np.asarray(up) - np.asarray(down)
    dw = dw[(dw > 0) & (dw < 2)]
    f += [m(dw), s(dw)]
    f.append(np.mean(dt > 0.5) if dt.size else np.nan)
    sec = ((ang[good] + np.pi) / (2 * np.pi) * 8).astype(int) % 8
    hist = np.bincount(sec, weights=ds[good], minlength=8)
    hist = hist / hist.sum() if hist.sum() > 0 else np.full(8, np.nan)
    f += list(hist)
    return np.asarray(f, dtype=np.float32)
