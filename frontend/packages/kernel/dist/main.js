var p = Object.defineProperty;
var w = (r, t, e) => t in r ? p(r, t, { enumerable: !0, configurable: !0, writable: !0, value: e }) : r[t] = e;
var c = (r, t, e) => w(r, typeof t != "symbol" ? t + "" : t, e);
class y {
  constructor() {
    c(this, "services", /* @__PURE__ */ new Map());
  }
  register(t, e) {
    this.services.has(t) && console.warn(`Service "${t}" is being overwritten.`), this.services.set(t, e);
  }
  resolve(t) {
    const e = this.services.get(t);
    if (!e)
      throw new Error(`Service "${t}" not found.`);
    return e;
  }
}
class m {
  constructor(t, e) {
    c(this, "manifests", []);
    c(this, "loadedPlugins", /* @__PURE__ */ new Map());
    this.apiService = t, this.hooks = e;
  }
  /**
   * 根据插件ID获取其清单文件。
   */
  getPluginManifest(t) {
    return this.manifests.find((e) => e.id === t);
  }
  /**
   * 聚合所有已加载插件的视图贡献。
   * @returns 一个以贡献点ID为键，贡献项数组为值的对象。
   */
  getAllViewContributions() {
    var e;
    const t = {};
    for (const [o, n] of this.loadedPlugins.entries()) {
      const s = (e = n.manifest.config.contributions) == null ? void 0 : e.views;
      if (s)
        for (const i in s) {
          t[i] || (t[i] = []);
          const g = s[i].map((h) => ({
            ...h,
            pluginId: o
          }));
          t[i].push(...g);
        }
    }
    return t;
  }
  /**
   * 从指定插件获取一个已注册的React组件。
   */
  getComponent(t, e) {
    var o;
    return (o = this.loadedPlugins.get(t)) == null ? void 0 : o.components.get(e);
  }
  /**
   * 启动完整的插件加载和初始化流程。这是内核启动过程的关键步骤。
   * 该流程被分为多个明确的阶段，以确保依赖关系正确处理。
   */
  async loadPlugins() {
    console.log("🔌 [Kernel] Starting plugin loading process...");
    try {
      this.manifests = await this.apiService.get("/api/plugins/manifest");
    } catch (e) {
      console.error("Fatal: Could not fetch plugin manifest from backend. Halting boot process.", e), this.hooks.trigger("system:fatal", { error: "Failed to load plugin manifest." });
      return;
    }
    const t = this.manifests.filter((e) => {
      var o;
      return e.type === "frontend" && ((o = e.config) == null ? void 0 : o.entryPoint);
    }).sort((e, o) => (e.config.priority ?? 50) - (o.config.priority ?? 50));
    console.log("  -> Phase 1: Loading all plugin scripts...");
    for (const e of t) {
      console.log(`     - Loading: ${e.id} (priority: ${e.config.priority})`);
      try {
        await this.loadModule(e.config.entryPoint);
        const o = window.__HEVNO_PENDING_PLUGIN__;
        if (!o) {
          console.warn(`Plugin ${e.id} was loaded but did not export a lifecycle via definePlugin.`);
          continue;
        }
        delete window.__HEVNO_PENDING_PLUGIN__, this.loadedPlugins.set(e.id, {
          manifest: e,
          lifecycle: o,
          components: /* @__PURE__ */ new Map()
          // 初始化组件注册表
        });
      } catch (o) {
        console.error(`Failed to load script for plugin: ${e.id} from ${e.config.entryPoint}`, o);
      }
    }
    console.log('  -> Phase 2: Executing "onLoad" lifecycle hooks...');
    for (const [e, o] of this.loadedPlugins.entries())
      if (o.lifecycle.onLoad) {
        const n = {
          registerComponent: (s, i) => {
            console.log(`[Plugin: ${e}] registered component: ${s}`), o.components.set(s, i);
          },
          getManifest: () => o.manifest
        };
        await Promise.resolve(o.lifecycle.onLoad(n));
      }
    console.log('  -> Phase 3: Executing "onActivate" lifecycle hooks...');
    for (const [, e] of this.loadedPlugins.entries())
      if (e.lifecycle.onActivate) {
        const o = {
          registerComponent: (n, s) => e.components.set(n, s),
          getManifest: () => e.manifest
        };
        await Promise.resolve(e.lifecycle.onActivate(o));
      }
    console.log("✅ [Kernel] All plugins loaded and activated."), this.hooks.trigger("plugins:ready");
  }
  /**
   * 使用现代的动态 `import()` 语法来加载一个JS模块。
   * 这比创建 <script> 标签更干净，并且能与 Vite 等现代构建工具无缝协作。
   * @param url - 插件入口文件的URL (例如: /plugins/core-layout/dist/index.js)
   * @private
   */
  loadModule(t) {
    return import(
      /* @vite-ignore */
      t
    );
  }
}
class P {
  constructor() {
    c(this, "events", /* @__PURE__ */ new Map());
  }
  on(t, e) {
    return this.events.has(t) || this.events.set(t, /* @__PURE__ */ new Set()), this.events.get(t).add(e), () => this.off(t, e);
  }
  off(t, e) {
    const o = this.events.get(t);
    o && o.delete(e);
  }
  emit(t, e) {
    const o = this.events.get(t);
    o && o.forEach((n) => {
      try {
        n(e);
      } catch (s) {
        console.error(`Error in event handler for "${t}":`, s);
      }
    });
  }
}
class v {
  constructor() {
    c(this, "hooks", /* @__PURE__ */ new Map());
  }
  addImplementation(t, e) {
    this.hooks.has(t) || this.hooks.set(t, /* @__PURE__ */ new Set()), this.hooks.get(t).add(e);
  }
  // “通知型”钩子，并发执行，不关心返回值
  async trigger(t, ...e) {
    const o = this.hooks.get(t);
    if (!o) return;
    const n = Array.from(o).map((s) => Promise.resolve(s(...e)));
    await Promise.all(n);
  }
  // “过滤型”钩子，串行链式执行
  async filter(t, e, ...o) {
    const n = this.hooks.get(t);
    if (!n) return e;
    let s = e;
    for (const i of Array.from(n))
      s = await Promise.resolve(i(s, ...o));
    return s;
  }
}
class E {
  constructor() {
    c(this, "requestInterceptors", []);
    c(this, "baseUrl", "http://localhost:8000");
  }
  addRequestInterceptor(t) {
    this.requestInterceptors.push(t);
  }
  async applyInterceptors(t) {
    let e = t;
    for (const o of this.requestInterceptors)
      e = await o(e);
    return e;
  }
  async get(t) {
    let e = new Request(`${this.baseUrl}${t}`, { method: "GET" });
    e = await this.applyInterceptors(e);
    const o = await fetch(e);
    if (!o.ok) throw new Error(`API Error: ${o.statusText}`);
    return o.json();
  }
  async post(t, e) {
    const o = new Request(`${this.baseUrl}${t}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(e)
    }), n = await this.applyInterceptors(o), s = await fetch(n);
    if (!s.ok) throw new Error(`API Error: ${s.statusText}`);
    return s.status === 204 ? null : s.json();
  }
  async put(t, e) {
    const o = new Request(`${this.baseUrl}${t}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(e)
    }), n = await this.applyInterceptors(o), s = await fetch(n);
    if (!s.ok) throw new Error(`API Error: ${s.statusText}`);
    return s.json();
  }
  async delete(t) {
    const e = new Request(`${this.baseUrl}${t}`, { method: "DELETE" }), o = await this.applyInterceptors(e), n = await fetch(o);
    if (!n.ok) throw new Error(`API Error: ${n.statusText}`);
    return n.json();
  }
}
const a = new y(), f = new P(), l = new v(), d = new E(), u = new m(d, l);
window.Hevno = {
  services: { registry: a, bus: f, hooks: l, api: d, plugins: u }
};
a.register("registry", a);
a.register("bus", f);
a.register("hooks", l);
a.register("api", d);
a.register("plugins", u);
document.addEventListener("DOMContentLoaded", () => {
  const r = document.getElementById("hevno-root") || (() => {
    const t = document.createElement("div");
    return t.id = "hevno-root", document.body.appendChild(t), t;
  })();
  l.trigger("kernel:ready", { rootEl: r }).then(() => {
    u.loadPlugins();
  });
});
