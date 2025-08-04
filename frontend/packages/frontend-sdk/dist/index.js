import { useMemo as f, useEffect as a, useState as v, useCallback as d } from "react";
function w(e) {
  return f(() => window.Hevno.services.registry.resolve(e), [e]);
}
function p(e, n) {
  const t = w("bus");
  a(() => {
    const o = t.on(e, n);
    return () => o();
  }, [t, e, n]);
}
function E(e, n = {}) {
  const { immediate: t = !0 } = n, [o, u] = v({
    data: null,
    isLoading: t,
    // 如果立即执行，初始状态就是加载中
    error: null
  }), c = d(
    async (...g) => {
      u((r) => ({ ...r, isLoading: !0, error: null }));
      try {
        const r = await e(...g);
        return u((i) => ({ ...i, data: r, isLoading: !1 })), r;
      } catch (r) {
        const i = r instanceof Error ? r : new Error(String(r));
        throw u((l) => ({ ...l, error: i, isLoading: !1, data: null })), i;
      }
    },
    [e]
    // 依赖于 apiCall 函数的引用
  );
  return a(() => {
    t && c();
  }, [c, t]), { ...o, execute: c };
}
function _(e) {
  window.__HEVNO_PENDING_PLUGIN__ = e;
}
const s = () => window.Hevno, y = {
  get api() {
    var e;
    return (e = s()) == null ? void 0 : e.services.api;
  },
  get bus() {
    var e;
    return (e = s()) == null ? void 0 : e.services.bus;
  },
  get hooks() {
    var e;
    return (e = s()) == null ? void 0 : e.services.hooks;
  },
  get registry() {
    var e;
    return (e = s()) == null ? void 0 : e.services.registry;
  },
  get plugins() {
    var e;
    return (e = s()) == null ? void 0 : e.services.plugins;
  }
};
export {
  _ as definePlugin,
  y as services,
  E as useApi,
  p as useEvent,
  w as useService
};
