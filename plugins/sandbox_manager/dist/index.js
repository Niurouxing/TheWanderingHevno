import { services as Se, useApi as dr, definePlugin as vr } from "@hevno/frontend-sdk";
import Ce, { useCallback as Te, useState as pr } from "react";
var H = { exports: {} }, I = {};
/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var we;
function gr() {
  if (we) return I;
  we = 1;
  var j = Ce, m = Symbol.for("react.element"), R = Symbol.for("react.fragment"), y = Object.prototype.hasOwnProperty, x = j.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner, S = { key: !0, ref: !0, __self: !0, __source: !0 };
  function T(E, f, g) {
    var c, _ = {}, C = null, W = null;
    g !== void 0 && (C = "" + g), f.key !== void 0 && (C = "" + f.key), f.ref !== void 0 && (W = f.ref);
    for (c in f) y.call(f, c) && !S.hasOwnProperty(c) && (_[c] = f[c]);
    if (E && E.defaultProps) for (c in f = E.defaultProps, f) _[c] === void 0 && (_[c] = f[c]);
    return { $$typeof: m, type: E, key: C, ref: W, props: _, _owner: x.current };
  }
  return I.Fragment = R, I.jsx = T, I.jsxs = T, I;
}
var $ = {};
/**
 * @license React
 * react-jsx-runtime.development.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var je;
function br() {
  return je || (je = 1, process.env.NODE_ENV !== "production" && function() {
    var j = Ce, m = Symbol.for("react.element"), R = Symbol.for("react.portal"), y = Symbol.for("react.fragment"), x = Symbol.for("react.strict_mode"), S = Symbol.for("react.profiler"), T = Symbol.for("react.provider"), E = Symbol.for("react.context"), f = Symbol.for("react.forward_ref"), g = Symbol.for("react.suspense"), c = Symbol.for("react.suspense_list"), _ = Symbol.for("react.memo"), C = Symbol.for("react.lazy"), W = Symbol.for("react.offscreen"), Z = Symbol.iterator, Oe = "@@iterator";
    function Pe(e) {
      if (e === null || typeof e != "object")
        return null;
      var r = Z && e[Z] || e[Oe];
      return typeof r == "function" ? r : null;
    }
    var k = j.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;
    function d(e) {
      {
        for (var r = arguments.length, t = new Array(r > 1 ? r - 1 : 0), n = 1; n < r; n++)
          t[n - 1] = arguments[n];
        ke("error", e, t);
      }
    }
    function ke(e, r, t) {
      {
        var n = k.ReactDebugCurrentFrame, o = n.getStackAddendum();
        o !== "" && (r += "%s", t = t.concat([o]));
        var s = t.map(function(i) {
          return String(i);
        });
        s.unshift("Warning: " + r), Function.prototype.apply.call(console[e], console, s);
      }
    }
    var De = !1, Fe = !1, Ae = !1, Ne = !1, Ie = !1, Q;
    Q = Symbol.for("react.module.reference");
    function $e(e) {
      return !!(typeof e == "string" || typeof e == "function" || e === y || e === S || Ie || e === x || e === g || e === c || Ne || e === W || De || Fe || Ae || typeof e == "object" && e !== null && (e.$$typeof === C || e.$$typeof === _ || e.$$typeof === T || e.$$typeof === E || e.$$typeof === f || // This needs to include all possible module reference object
      // types supported by any Flight configuration anywhere since
      // we don't know which Flight build this will end up being used
      // with.
      e.$$typeof === Q || e.getModuleId !== void 0));
    }
    function We(e, r, t) {
      var n = e.displayName;
      if (n)
        return n;
      var o = r.displayName || r.name || "";
      return o !== "" ? t + "(" + o + ")" : t;
    }
    function ee(e) {
      return e.displayName || "Context";
    }
    function w(e) {
      if (e == null)
        return null;
      if (typeof e.tag == "number" && d("Received an unexpected object in getComponentNameFromType(). This is likely a bug in React. Please file an issue."), typeof e == "function")
        return e.displayName || e.name || null;
      if (typeof e == "string")
        return e;
      switch (e) {
        case y:
          return "Fragment";
        case R:
          return "Portal";
        case S:
          return "Profiler";
        case x:
          return "StrictMode";
        case g:
          return "Suspense";
        case c:
          return "SuspenseList";
      }
      if (typeof e == "object")
        switch (e.$$typeof) {
          case E:
            var r = e;
            return ee(r) + ".Consumer";
          case T:
            var t = e;
            return ee(t._context) + ".Provider";
          case f:
            return We(e, e.render, "ForwardRef");
          case _:
            var n = e.displayName || null;
            return n !== null ? n : w(e.type) || "Memo";
          case C: {
            var o = e, s = o._payload, i = o._init;
            try {
              return w(i(s));
            } catch {
              return null;
            }
          }
        }
      return null;
    }
    var O = Object.assign, A = 0, re, te, ne, ae, ie, oe, se;
    function ue() {
    }
    ue.__reactDisabledLog = !0;
    function Ye() {
      {
        if (A === 0) {
          re = console.log, te = console.info, ne = console.warn, ae = console.error, ie = console.group, oe = console.groupCollapsed, se = console.groupEnd;
          var e = {
            configurable: !0,
            enumerable: !0,
            value: ue,
            writable: !0
          };
          Object.defineProperties(console, {
            info: e,
            log: e,
            warn: e,
            error: e,
            group: e,
            groupCollapsed: e,
            groupEnd: e
          });
        }
        A++;
      }
    }
    function Le() {
      {
        if (A--, A === 0) {
          var e = {
            configurable: !0,
            enumerable: !0,
            writable: !0
          };
          Object.defineProperties(console, {
            log: O({}, e, {
              value: re
            }),
            info: O({}, e, {
              value: te
            }),
            warn: O({}, e, {
              value: ne
            }),
            error: O({}, e, {
              value: ae
            }),
            group: O({}, e, {
              value: ie
            }),
            groupCollapsed: O({}, e, {
              value: oe
            }),
            groupEnd: O({}, e, {
              value: se
            })
          });
        }
        A < 0 && d("disabledDepth fell below zero. This is a bug in React. Please file an issue.");
      }
    }
    var U = k.ReactCurrentDispatcher, B;
    function Y(e, r, t) {
      {
        if (B === void 0)
          try {
            throw Error();
          } catch (o) {
            var n = o.stack.trim().match(/\n( *(at )?)/);
            B = n && n[1] || "";
          }
        return `
` + B + e;
      }
    }
    var J = !1, L;
    {
      var Ve = typeof WeakMap == "function" ? WeakMap : Map;
      L = new Ve();
    }
    function le(e, r) {
      if (!e || J)
        return "";
      {
        var t = L.get(e);
        if (t !== void 0)
          return t;
      }
      var n;
      J = !0;
      var o = Error.prepareStackTrace;
      Error.prepareStackTrace = void 0;
      var s;
      s = U.current, U.current = null, Ye();
      try {
        if (r) {
          var i = function() {
            throw Error();
          };
          if (Object.defineProperty(i.prototype, "props", {
            set: function() {
              throw Error();
            }
          }), typeof Reflect == "object" && Reflect.construct) {
            try {
              Reflect.construct(i, []);
            } catch (p) {
              n = p;
            }
            Reflect.construct(e, [], i);
          } else {
            try {
              i.call();
            } catch (p) {
              n = p;
            }
            e.call(i.prototype);
          }
        } else {
          try {
            throw Error();
          } catch (p) {
            n = p;
          }
          e();
        }
      } catch (p) {
        if (p && n && typeof p.stack == "string") {
          for (var a = p.stack.split(`
`), v = n.stack.split(`
`), u = a.length - 1, l = v.length - 1; u >= 1 && l >= 0 && a[u] !== v[l]; )
            l--;
          for (; u >= 1 && l >= 0; u--, l--)
            if (a[u] !== v[l]) {
              if (u !== 1 || l !== 1)
                do
                  if (u--, l--, l < 0 || a[u] !== v[l]) {
                    var h = `
` + a[u].replace(" at new ", " at ");
                    return e.displayName && h.includes("<anonymous>") && (h = h.replace("<anonymous>", e.displayName)), typeof e == "function" && L.set(e, h), h;
                  }
                while (u >= 1 && l >= 0);
              break;
            }
        }
      } finally {
        J = !1, U.current = s, Le(), Error.prepareStackTrace = o;
      }
      var F = e ? e.displayName || e.name : "", P = F ? Y(F) : "";
      return typeof e == "function" && L.set(e, P), P;
    }
    function Me(e, r, t) {
      return le(e, !1);
    }
    function Ue(e) {
      var r = e.prototype;
      return !!(r && r.isReactComponent);
    }
    function V(e, r, t) {
      if (e == null)
        return "";
      if (typeof e == "function")
        return le(e, Ue(e));
      if (typeof e == "string")
        return Y(e);
      switch (e) {
        case g:
          return Y("Suspense");
        case c:
          return Y("SuspenseList");
      }
      if (typeof e == "object")
        switch (e.$$typeof) {
          case f:
            return Me(e.render);
          case _:
            return V(e.type, r, t);
          case C: {
            var n = e, o = n._payload, s = n._init;
            try {
              return V(s(o), r, t);
            } catch {
            }
          }
        }
      return "";
    }
    var N = Object.prototype.hasOwnProperty, ce = {}, fe = k.ReactDebugCurrentFrame;
    function M(e) {
      if (e) {
        var r = e._owner, t = V(e.type, e._source, r ? r.type : null);
        fe.setExtraStackFrame(t);
      } else
        fe.setExtraStackFrame(null);
    }
    function Be(e, r, t, n, o) {
      {
        var s = Function.call.bind(N);
        for (var i in e)
          if (s(e, i)) {
            var a = void 0;
            try {
              if (typeof e[i] != "function") {
                var v = Error((n || "React class") + ": " + t + " type `" + i + "` is invalid; it must be a function, usually from the `prop-types` package, but received `" + typeof e[i] + "`.This often happens because of typos such as `PropTypes.function` instead of `PropTypes.func`.");
                throw v.name = "Invariant Violation", v;
              }
              a = e[i](r, i, n, t, null, "SECRET_DO_NOT_PASS_THIS_OR_YOU_WILL_BE_FIRED");
            } catch (u) {
              a = u;
            }
            a && !(a instanceof Error) && (M(o), d("%s: type specification of %s `%s` is invalid; the type checker function must return `null` or an `Error` but returned a %s. You may have forgotten to pass an argument to the type checker creator (arrayOf, instanceOf, objectOf, oneOf, oneOfType, and shape all require an argument).", n || "React class", t, i, typeof a), M(null)), a instanceof Error && !(a.message in ce) && (ce[a.message] = !0, M(o), d("Failed %s type: %s", t, a.message), M(null));
          }
      }
    }
    var Je = Array.isArray;
    function q(e) {
      return Je(e);
    }
    function qe(e) {
      {
        var r = typeof Symbol == "function" && Symbol.toStringTag, t = r && e[Symbol.toStringTag] || e.constructor.name || "Object";
        return t;
      }
    }
    function Ke(e) {
      try {
        return de(e), !1;
      } catch {
        return !0;
      }
    }
    function de(e) {
      return "" + e;
    }
    function ve(e) {
      if (Ke(e))
        return d("The provided key is an unsupported type %s. This value must be coerced to a string before before using it here.", qe(e)), de(e);
    }
    var pe = k.ReactCurrentOwner, Ge = {
      key: !0,
      ref: !0,
      __self: !0,
      __source: !0
    }, ge, be;
    function ze(e) {
      if (N.call(e, "ref")) {
        var r = Object.getOwnPropertyDescriptor(e, "ref").get;
        if (r && r.isReactWarning)
          return !1;
      }
      return e.ref !== void 0;
    }
    function Xe(e) {
      if (N.call(e, "key")) {
        var r = Object.getOwnPropertyDescriptor(e, "key").get;
        if (r && r.isReactWarning)
          return !1;
      }
      return e.key !== void 0;
    }
    function He(e, r) {
      typeof e.ref == "string" && pe.current;
    }
    function Ze(e, r) {
      {
        var t = function() {
          ge || (ge = !0, d("%s: `key` is not a prop. Trying to access it will result in `undefined` being returned. If you need to access the same value within the child component, you should pass it as a different prop. (https://reactjs.org/link/special-props)", r));
        };
        t.isReactWarning = !0, Object.defineProperty(e, "key", {
          get: t,
          configurable: !0
        });
      }
    }
    function Qe(e, r) {
      {
        var t = function() {
          be || (be = !0, d("%s: `ref` is not a prop. Trying to access it will result in `undefined` being returned. If you need to access the same value within the child component, you should pass it as a different prop. (https://reactjs.org/link/special-props)", r));
        };
        t.isReactWarning = !0, Object.defineProperty(e, "ref", {
          get: t,
          configurable: !0
        });
      }
    }
    var er = function(e, r, t, n, o, s, i) {
      var a = {
        // This tag allows us to uniquely identify this as a React Element
        $$typeof: m,
        // Built-in properties that belong on the element
        type: e,
        key: r,
        ref: t,
        props: i,
        // Record the component responsible for creating this element.
        _owner: s
      };
      return a._store = {}, Object.defineProperty(a._store, "validated", {
        configurable: !1,
        enumerable: !1,
        writable: !0,
        value: !1
      }), Object.defineProperty(a, "_self", {
        configurable: !1,
        enumerable: !1,
        writable: !1,
        value: n
      }), Object.defineProperty(a, "_source", {
        configurable: !1,
        enumerable: !1,
        writable: !1,
        value: o
      }), Object.freeze && (Object.freeze(a.props), Object.freeze(a)), a;
    };
    function rr(e, r, t, n, o) {
      {
        var s, i = {}, a = null, v = null;
        t !== void 0 && (ve(t), a = "" + t), Xe(r) && (ve(r.key), a = "" + r.key), ze(r) && (v = r.ref, He(r, o));
        for (s in r)
          N.call(r, s) && !Ge.hasOwnProperty(s) && (i[s] = r[s]);
        if (e && e.defaultProps) {
          var u = e.defaultProps;
          for (s in u)
            i[s] === void 0 && (i[s] = u[s]);
        }
        if (a || v) {
          var l = typeof e == "function" ? e.displayName || e.name || "Unknown" : e;
          a && Ze(i, l), v && Qe(i, l);
        }
        return er(e, a, v, o, n, pe.current, i);
      }
    }
    var K = k.ReactCurrentOwner, he = k.ReactDebugCurrentFrame;
    function D(e) {
      if (e) {
        var r = e._owner, t = V(e.type, e._source, r ? r.type : null);
        he.setExtraStackFrame(t);
      } else
        he.setExtraStackFrame(null);
    }
    var G;
    G = !1;
    function z(e) {
      return typeof e == "object" && e !== null && e.$$typeof === m;
    }
    function me() {
      {
        if (K.current) {
          var e = w(K.current.type);
          if (e)
            return `

Check the render method of \`` + e + "`.";
        }
        return "";
      }
    }
    function tr(e) {
      return "";
    }
    var ye = {};
    function nr(e) {
      {
        var r = me();
        if (!r) {
          var t = typeof e == "string" ? e : e.displayName || e.name;
          t && (r = `

Check the top-level render call using <` + t + ">.");
        }
        return r;
      }
    }
    function Ee(e, r) {
      {
        if (!e._store || e._store.validated || e.key != null)
          return;
        e._store.validated = !0;
        var t = nr(r);
        if (ye[t])
          return;
        ye[t] = !0;
        var n = "";
        e && e._owner && e._owner !== K.current && (n = " It was passed a child from " + w(e._owner.type) + "."), D(e), d('Each child in a list should have a unique "key" prop.%s%s See https://reactjs.org/link/warning-keys for more information.', t, n), D(null);
      }
    }
    function _e(e, r) {
      {
        if (typeof e != "object")
          return;
        if (q(e))
          for (var t = 0; t < e.length; t++) {
            var n = e[t];
            z(n) && Ee(n, r);
          }
        else if (z(e))
          e._store && (e._store.validated = !0);
        else if (e) {
          var o = Pe(e);
          if (typeof o == "function" && o !== e.entries)
            for (var s = o.call(e), i; !(i = s.next()).done; )
              z(i.value) && Ee(i.value, r);
        }
      }
    }
    function ar(e) {
      {
        var r = e.type;
        if (r == null || typeof r == "string")
          return;
        var t;
        if (typeof r == "function")
          t = r.propTypes;
        else if (typeof r == "object" && (r.$$typeof === f || // Note: Memo only checks outer props here.
        // Inner props are checked in the reconciler.
        r.$$typeof === _))
          t = r.propTypes;
        else
          return;
        if (t) {
          var n = w(r);
          Be(t, e.props, "prop", n, e);
        } else if (r.PropTypes !== void 0 && !G) {
          G = !0;
          var o = w(r);
          d("Component %s declared `PropTypes` instead of `propTypes`. Did you misspell the property assignment?", o || "Unknown");
        }
        typeof r.getDefaultProps == "function" && !r.getDefaultProps.isReactClassApproved && d("getDefaultProps is only used on classic React.createClass definitions. Use a static property named `defaultProps` instead.");
      }
    }
    function ir(e) {
      {
        for (var r = Object.keys(e.props), t = 0; t < r.length; t++) {
          var n = r[t];
          if (n !== "children" && n !== "key") {
            D(e), d("Invalid prop `%s` supplied to `React.Fragment`. React.Fragment can only have `key` and `children` props.", n), D(null);
            break;
          }
        }
        e.ref !== null && (D(e), d("Invalid attribute `ref` supplied to `React.Fragment`."), D(null));
      }
    }
    var Re = {};
    function xe(e, r, t, n, o, s) {
      {
        var i = $e(e);
        if (!i) {
          var a = "";
          (e === void 0 || typeof e == "object" && e !== null && Object.keys(e).length === 0) && (a += " You likely forgot to export your component from the file it's defined in, or you might have mixed up default and named imports.");
          var v = tr();
          v ? a += v : a += me();
          var u;
          e === null ? u = "null" : q(e) ? u = "array" : e !== void 0 && e.$$typeof === m ? (u = "<" + (w(e.type) || "Unknown") + " />", a = " Did you accidentally export a JSX literal instead of a component?") : u = typeof e, d("React.jsx: type is invalid -- expected a string (for built-in components) or a class/function (for composite components) but got: %s.%s", u, a);
        }
        var l = rr(e, r, t, o, s);
        if (l == null)
          return l;
        if (i) {
          var h = r.children;
          if (h !== void 0)
            if (n)
              if (q(h)) {
                for (var F = 0; F < h.length; F++)
                  _e(h[F], e);
                Object.freeze && Object.freeze(h);
              } else
                d("React.jsx: Static children should always be an array. You are likely explicitly calling React.jsxs or React.jsxDEV. Use the Babel transform instead.");
            else
              _e(h, e);
        }
        if (N.call(r, "key")) {
          var P = w(e), p = Object.keys(r).filter(function(fr) {
            return fr !== "key";
          }), X = p.length > 0 ? "{key: someKey, " + p.join(": ..., ") + ": ...}" : "{key: someKey}";
          if (!Re[P + X]) {
            var cr = p.length > 0 ? "{" + p.join(": ..., ") + ": ...}" : "{}";
            d(`A props object containing a "key" prop is being spread into JSX:
  let props = %s;
  <%s {...props} />
React keys must be passed directly to JSX without using spread:
  let props = %s;
  <%s key={someKey} {...props} />`, X, P, cr, P), Re[P + X] = !0;
          }
        }
        return e === y ? ir(l) : ar(l), l;
      }
    }
    function or(e, r, t) {
      return xe(e, r, t, !0);
    }
    function sr(e, r, t) {
      return xe(e, r, t, !1);
    }
    var ur = sr, lr = or;
    $.Fragment = y, $.jsx = ur, $.jsxs = lr;
  }()), $;
}
process.env.NODE_ENV === "production" ? H.exports = gr() : H.exports = br();
var b = H.exports;
function hr() {
  const j = Te(() => Se.api.get("/api/sandboxes"), []), { data: m, isLoading: R, error: y, execute: x } = dr(j), [S, T] = pr(!1), E = () => R ? /* @__PURE__ */ b.jsx("p", { className: "text-gray-400", children: "Loading sandboxes..." }) : y ? /* @__PURE__ */ b.jsxs("p", { className: "text-red-400", children: [
    "Error: ",
    y.message
  ] }) : !m || m.length === 0 ? /* @__PURE__ */ b.jsx("p", { className: "text-gray-500", children: "No sandboxes found." }) : /* @__PURE__ */ b.jsx("ul", { className: "space-y-2", children: m.map((g) => /* @__PURE__ */ b.jsxs("li", { className: "p-2 bg-gray-700 rounded hover:bg-gray-600 cursor-pointer", children: [
    /* @__PURE__ */ b.jsx("p", { className: "font-semibold text-white", children: g.name }),
    /* @__PURE__ */ b.jsx("p", { className: "text-xs text-gray-400 truncate", children: g.id })
  ] }, g.id)) }), f = Te(async () => {
    const g = window.prompt("Enter new sandbox name:", "New Sandbox");
    if (g) {
      T(!0);
      try {
        const c = {
          name: g,
          // 根据后端文档，提供一个最小化的图和初始状态
          graph_collection: {
            main: {
              nodes: [
                {
                  id: "start",
                  run: [{ runtime: "system.io.log", config: { message: "Genesis." } }]
                }
              ]
            }
          },
          initial_state: {}
        };
        await Se.api.post("/api/sandboxes", c), x();
      } catch (c) {
        alert(`Failed to create sandbox: ${c instanceof Error ? c.message : String(c)}`);
      } finally {
        T(!1);
      }
    }
  }, [x]);
  return /* @__PURE__ */ b.jsxs("div", { className: "p-2", children: [
    /* @__PURE__ */ b.jsxs("div", { className: "flex justify-between items-center mb-2", children: [
      /* @__PURE__ */ b.jsx("h3", { className: "text-lg font-bold text-white", children: "Sandboxes" }),
      /* @__PURE__ */ b.jsxs("div", { className: "flex space-x-2", children: [
        /* @__PURE__ */ b.jsx(
          "button",
          {
            onClick: f,
            disabled: R || S,
            className: "px-2 py-1 text-xs bg-green-600 rounded hover:bg-green-500 disabled:opacity-50",
            children: S ? "..." : "+ New"
          }
        ),
        /* @__PURE__ */ b.jsx(
          "button",
          {
            onClick: () => x(),
            disabled: R || S,
            className: "px-2 py-1 text-xs bg-blue-600 rounded hover:bg-blue-500 disabled:opacity-50",
            children: R ? "..." : "Refresh"
          }
        )
      ] })
    ] }),
    E()
  ] });
}
const Er = vr({
  onLoad: (j) => {
    j.registerComponent("SandboxList", hr);
  }
});
export {
  Er as default
};
