import { useService as Oc, definePlugin as Tc, services as Hn } from "@hevno/frontend-sdk";
import * as Be from "react";
import ct, { forwardRef as lt, useContext as gt, createContext as Mc, createElement as nn, useRef as be, useLayoutEffect as kc, useImperativeHandle as Mt, useState as Ke, useEffect as De, useCallback as Ae, useMemo as Ec } from "react";
var Qn = { exports: {} }, ln = {};
/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var xt;
function Uc() {
  if (xt) return ln;
  xt = 1;
  var e = ct, n = Symbol.for("react.element"), t = Symbol.for("react.fragment"), c = Object.prototype.hasOwnProperty, g = e.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner, r = { key: !0, ref: !0, __self: !0, __source: !0 };
  function i(I, a, s) {
    var b, C = {}, u = null, W = null;
    s !== void 0 && (u = "" + s), a.key !== void 0 && (u = "" + a.key), a.ref !== void 0 && (W = a.ref);
    for (b in a) c.call(a, b) && !r.hasOwnProperty(b) && (C[b] = a[b]);
    if (I && I.defaultProps) for (b in a = I.defaultProps, a) C[b] === void 0 && (C[b] = a[b]);
    return { $$typeof: n, type: I, key: u, ref: W, props: C, _owner: g.current };
  }
  return ln.Fragment = t, ln.jsx = i, ln.jsxs = i, ln;
}
var gn = {};
/**
 * @license React
 * react-jsx-runtime.development.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var vt;
function Hc() {
  return vt || (vt = 1, process.env.NODE_ENV !== "production" && function() {
    var e = ct, n = Symbol.for("react.element"), t = Symbol.for("react.portal"), c = Symbol.for("react.fragment"), g = Symbol.for("react.strict_mode"), r = Symbol.for("react.profiler"), i = Symbol.for("react.provider"), I = Symbol.for("react.context"), a = Symbol.for("react.forward_ref"), s = Symbol.for("react.suspense"), b = Symbol.for("react.suspense_list"), C = Symbol.for("react.memo"), u = Symbol.for("react.lazy"), W = Symbol.for("react.offscreen"), d = Symbol.iterator, x = "@@iterator";
    function v(l) {
      if (l === null || typeof l != "object")
        return null;
      var o = d && l[d] || l[x];
      return typeof o == "function" ? o : null;
    }
    var m = e.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;
    function p(l) {
      {
        for (var o = arguments.length, Z = new Array(o > 1 ? o - 1 : 0), B = 1; B < o; B++)
          Z[B - 1] = arguments[B];
        h("error", l, Z);
      }
    }
    function h(l, o, Z) {
      {
        var B = m.ReactDebugCurrentFrame, D = B.getStackAddendum();
        D !== "" && (o += "%s", Z = Z.concat([D]));
        var E = Z.map(function(j) {
          return String(j);
        });
        E.unshift("Warning: " + o), Function.prototype.apply.call(console[l], console, E);
      }
    }
    var L = !1, A = !1, z = !1, f = !1, ae = !1, Ce;
    Ce = Symbol.for("react.module.reference");
    function ge(l) {
      return !!(typeof l == "string" || typeof l == "function" || l === c || l === r || ae || l === g || l === s || l === b || f || l === W || L || A || z || typeof l == "object" && l !== null && (l.$$typeof === u || l.$$typeof === C || l.$$typeof === i || l.$$typeof === I || l.$$typeof === a || // This needs to include all possible module reference object
      // types supported by any Flight configuration anywhere since
      // we don't know which Flight build this will end up being used
      // with.
      l.$$typeof === Ce || l.getModuleId !== void 0));
    }
    function te(l, o, Z) {
      var B = l.displayName;
      if (B)
        return B;
      var D = o.displayName || o.name || "";
      return D !== "" ? Z + "(" + D + ")" : Z;
    }
    function U(l) {
      return l.displayName || "Context";
    }
    function ce(l) {
      if (l == null)
        return null;
      if (typeof l.tag == "number" && p("Received an unexpected object in getComponentNameFromType(). This is likely a bug in React. Please file an issue."), typeof l == "function")
        return l.displayName || l.name || null;
      if (typeof l == "string")
        return l;
      switch (l) {
        case c:
          return "Fragment";
        case t:
          return "Portal";
        case r:
          return "Profiler";
        case g:
          return "StrictMode";
        case s:
          return "Suspense";
        case b:
          return "SuspenseList";
      }
      if (typeof l == "object")
        switch (l.$$typeof) {
          case I:
            var o = l;
            return U(o) + ".Consumer";
          case i:
            var Z = l;
            return U(Z._context) + ".Provider";
          case a:
            return te(l, l.render, "ForwardRef");
          case C:
            var B = l.displayName || null;
            return B !== null ? B : ce(l.type) || "Memo";
          case u: {
            var D = l, E = D._payload, j = D._init;
            try {
              return ce(j(E));
            } catch {
              return null;
            }
          }
        }
      return null;
    }
    var H = Object.assign, Q = 0, q, xe, ye, ve, Re, We, Ve;
    function y() {
    }
    y.__reactDisabledLog = !0;
    function Y() {
      {
        if (Q === 0) {
          q = console.log, xe = console.info, ye = console.warn, ve = console.error, Re = console.group, We = console.groupCollapsed, Ve = console.groupEnd;
          var l = {
            configurable: !0,
            enumerable: !0,
            value: y,
            writable: !0
          };
          Object.defineProperties(console, {
            info: l,
            log: l,
            warn: l,
            error: l,
            group: l,
            groupCollapsed: l,
            groupEnd: l
          });
        }
        Q++;
      }
    }
    function R() {
      {
        if (Q--, Q === 0) {
          var l = {
            configurable: !0,
            enumerable: !0,
            writable: !0
          };
          Object.defineProperties(console, {
            log: H({}, l, {
              value: q
            }),
            info: H({}, l, {
              value: xe
            }),
            warn: H({}, l, {
              value: ye
            }),
            error: H({}, l, {
              value: ve
            }),
            group: H({}, l, {
              value: Re
            }),
            groupCollapsed: H({}, l, {
              value: We
            }),
            groupEnd: H({}, l, {
              value: Ve
            })
          });
        }
        Q < 0 && p("disabledDepth fell below zero. This is a bug in React. Please file an issue.");
      }
    }
    var V = m.ReactCurrentDispatcher, X;
    function N(l, o, Z) {
      {
        if (X === void 0)
          try {
            throw Error();
          } catch (D) {
            var B = D.stack.trim().match(/\n( *(at )?)/);
            X = B && B[1] || "";
          }
        return `
` + X + l;
      }
    }
    var F = !1, k;
    {
      var ue = typeof WeakMap == "function" ? WeakMap : Map;
      k = new ue();
    }
    function G(l, o) {
      if (!l || F)
        return "";
      {
        var Z = k.get(l);
        if (Z !== void 0)
          return Z;
      }
      var B;
      F = !0;
      var D = Error.prepareStackTrace;
      Error.prepareStackTrace = void 0;
      var E;
      E = V.current, V.current = null, Y();
      try {
        if (o) {
          var j = function() {
            throw Error();
          };
          if (Object.defineProperty(j.prototype, "props", {
            set: function() {
              throw Error();
            }
          }), typeof Reflect == "object" && Reflect.construct) {
            try {
              Reflect.construct(j, []);
            } catch (se) {
              B = se;
            }
            Reflect.construct(l, [], j);
          } else {
            try {
              j.call();
            } catch (se) {
              B = se;
            }
            l.call(j.prototype);
          }
        } else {
          try {
            throw Error();
          } catch (se) {
            B = se;
          }
          l();
        }
      } catch (se) {
        if (se && B && typeof se.stack == "string") {
          for (var w = se.stack.split(`
`), oe = B.stack.split(`
`), K = w.length - 1, ee = oe.length - 1; K >= 1 && ee >= 0 && w[K] !== oe[ee]; )
            ee--;
          for (; K >= 1 && ee >= 0; K--, ee--)
            if (w[K] !== oe[ee]) {
              if (K !== 1 || ee !== 1)
                do
                  if (K--, ee--, ee < 0 || w[K] !== oe[ee]) {
                    var fe = `
` + w[K].replace(" at new ", " at ");
                    return l.displayName && fe.includes("<anonymous>") && (fe = fe.replace("<anonymous>", l.displayName)), typeof l == "function" && k.set(l, fe), fe;
                  }
                while (K >= 1 && ee >= 0);
              break;
            }
        }
      } finally {
        F = !1, V.current = E, R(), Error.prepareStackTrace = D;
      }
      var Ue = l ? l.displayName || l.name : "", Fe = Ue ? N(Ue) : "";
      return typeof l == "function" && k.set(l, Fe), Fe;
    }
    function M(l, o, Z) {
      return G(l, !1);
    }
    function le(l) {
      var o = l.prototype;
      return !!(o && o.isReactComponent);
    }
    function me(l, o, Z) {
      if (l == null)
        return "";
      if (typeof l == "function")
        return G(l, le(l));
      if (typeof l == "string")
        return N(l);
      switch (l) {
        case s:
          return N("Suspense");
        case b:
          return N("SuspenseList");
      }
      if (typeof l == "object")
        switch (l.$$typeof) {
          case a:
            return M(l.render);
          case C:
            return me(l.type, o, Z);
          case u: {
            var B = l, D = B._payload, E = B._init;
            try {
              return me(E(D), o, Z);
            } catch {
            }
          }
        }
      return "";
    }
    var he = Object.prototype.hasOwnProperty, Me = {}, re = m.ReactDebugCurrentFrame;
    function we(l) {
      if (l) {
        var o = l._owner, Z = me(l.type, l._source, o ? o.type : null);
        re.setExtraStackFrame(Z);
      } else
        re.setExtraStackFrame(null);
    }
    function wn(l, o, Z, B, D) {
      {
        var E = Function.call.bind(he);
        for (var j in l)
          if (E(l, j)) {
            var w = void 0;
            try {
              if (typeof l[j] != "function") {
                var oe = Error((B || "React class") + ": " + Z + " type `" + j + "` is invalid; it must be a function, usually from the `prop-types` package, but received `" + typeof l[j] + "`.This often happens because of typos such as `PropTypes.function` instead of `PropTypes.func`.");
                throw oe.name = "Invariant Violation", oe;
              }
              w = l[j](o, j, B, Z, null, "SECRET_DO_NOT_PASS_THIS_OR_YOU_WILL_BE_FIRED");
            } catch (K) {
              w = K;
            }
            w && !(w instanceof Error) && (we(D), p("%s: type specification of %s `%s` is invalid; the type checker function must return `null` or an `Error` but returned a %s. You may have forgotten to pass an argument to the type checker creator (arrayOf, instanceOf, objectOf, oneOf, oneOfType, and shape all require an argument).", B || "React class", Z, j, typeof w), we(null)), w instanceof Error && !(w.message in Me) && (Me[w.message] = !0, we(D), p("Failed %s type: %s", Z, w.message), we(null));
          }
      }
    }
    var je = Array.isArray;
    function ke(l) {
      return je(l);
    }
    function jn(l) {
      {
        var o = typeof Symbol == "function" && Symbol.toStringTag, Z = o && l[Symbol.toStringTag] || l.constructor.name || "Object";
        return Z;
      }
    }
    function pc(l) {
      try {
        return st(l), !1;
      } catch {
        return !0;
      }
    }
    function st(l) {
      return "" + l;
    }
    function At(l) {
      if (pc(l))
        return p("The provided key is an unsupported type %s. This value must be coerced to a string before before using it here.", jn(l)), st(l);
    }
    var bt = m.ReactCurrentOwner, Xc = {
      key: !0,
      ref: !0,
      __self: !0,
      __source: !0
    }, dt, mt;
    function xc(l) {
      if (he.call(l, "ref")) {
        var o = Object.getOwnPropertyDescriptor(l, "ref").get;
        if (o && o.isReactWarning)
          return !1;
      }
      return l.ref !== void 0;
    }
    function vc(l) {
      if (he.call(l, "key")) {
        var o = Object.getOwnPropertyDescriptor(l, "key").get;
        if (o && o.isReactWarning)
          return !1;
      }
      return l.key !== void 0;
    }
    function Vc(l, o) {
      typeof l.ref == "string" && bt.current;
    }
    function hc(l, o) {
      {
        var Z = function() {
          dt || (dt = !0, p("%s: `key` is not a prop. Trying to access it will result in `undefined` being returned. If you need to access the same value within the child component, you should pass it as a different prop. (https://reactjs.org/link/special-props)", o));
        };
        Z.isReactWarning = !0, Object.defineProperty(l, "key", {
          get: Z,
          configurable: !0
        });
      }
    }
    function Yc(l, o) {
      {
        var Z = function() {
          mt || (mt = !0, p("%s: `ref` is not a prop. Trying to access it will result in `undefined` being returned. If you need to access the same value within the child component, you should pass it as a different prop. (https://reactjs.org/link/special-props)", o));
        };
        Z.isReactWarning = !0, Object.defineProperty(l, "ref", {
          get: Z,
          configurable: !0
        });
      }
    }
    var Nc = function(l, o, Z, B, D, E, j) {
      var w = {
        // This tag allows us to uniquely identify this as a React Element
        $$typeof: n,
        // Built-in properties that belong on the element
        type: l,
        key: o,
        ref: Z,
        props: j,
        // Record the component responsible for creating this element.
        _owner: E
      };
      return w._store = {}, Object.defineProperty(w._store, "validated", {
        configurable: !1,
        enumerable: !1,
        writable: !0,
        value: !1
      }), Object.defineProperty(w, "_self", {
        configurable: !1,
        enumerable: !1,
        writable: !1,
        value: B
      }), Object.defineProperty(w, "_source", {
        configurable: !1,
        enumerable: !1,
        writable: !1,
        value: D
      }), Object.freeze && (Object.freeze(w.props), Object.freeze(w)), w;
    };
    function Bc(l, o, Z, B, D) {
      {
        var E, j = {}, w = null, oe = null;
        Z !== void 0 && (At(Z), w = "" + Z), vc(o) && (At(o.key), w = "" + o.key), xc(o) && (oe = o.ref, Vc(o, D));
        for (E in o)
          he.call(o, E) && !Xc.hasOwnProperty(E) && (j[E] = o[E]);
        if (l && l.defaultProps) {
          var K = l.defaultProps;
          for (E in K)
            j[E] === void 0 && (j[E] = K[E]);
        }
        if (w || oe) {
          var ee = typeof l == "function" ? l.displayName || l.name || "Unknown" : l;
          w && hc(j, ee), oe && Yc(j, ee);
        }
        return Nc(l, w, oe, D, B, bt.current, j);
      }
    }
    var Fn = m.ReactCurrentOwner, Zt = m.ReactDebugCurrentFrame;
    function Ee(l) {
      if (l) {
        var o = l._owner, Z = me(l.type, l._source, o ? o.type : null);
        Zt.setExtraStackFrame(Z);
      } else
        Zt.setExtraStackFrame(null);
    }
    var Sn;
    Sn = !1;
    function Pn(l) {
      return typeof l == "object" && l !== null && l.$$typeof === n;
    }
    function Gt() {
      {
        if (Fn.current) {
          var l = ce(Fn.current.type);
          if (l)
            return `

Check the render method of \`` + l + "`.";
        }
        return "";
      }
    }
    function zc(l) {
      return "";
    }
    var ft = {};
    function Rc(l) {
      {
        var o = Gt();
        if (!o) {
          var Z = typeof l == "string" ? l : l.displayName || l.name;
          Z && (o = `

Check the top-level render call using <` + Z + ">.");
        }
        return o;
      }
    }
    function yt(l, o) {
      {
        if (!l._store || l._store.validated || l.key != null)
          return;
        l._store.validated = !0;
        var Z = Rc(o);
        if (ft[Z])
          return;
        ft[Z] = !0;
        var B = "";
        l && l._owner && l._owner !== Fn.current && (B = " It was passed a child from " + ce(l._owner.type) + "."), Ee(l), p('Each child in a list should have a unique "key" prop.%s%s See https://reactjs.org/link/warning-keys for more information.', Z, B), Ee(null);
      }
    }
    function Wt(l, o) {
      {
        if (typeof l != "object")
          return;
        if (ke(l))
          for (var Z = 0; Z < l.length; Z++) {
            var B = l[Z];
            Pn(B) && yt(B, o);
          }
        else if (Pn(l))
          l._store && (l._store.validated = !0);
        else if (l) {
          var D = v(l);
          if (typeof D == "function" && D !== l.entries)
            for (var E = D.call(l), j; !(j = E.next()).done; )
              Pn(j.value) && yt(j.value, o);
        }
      }
    }
    function Lc(l) {
      {
        var o = l.type;
        if (o == null || typeof o == "string")
          return;
        var Z;
        if (typeof o == "function")
          Z = o.propTypes;
        else if (typeof o == "object" && (o.$$typeof === a || // Note: Memo only checks outer props here.
        // Inner props are checked in the reconciler.
        o.$$typeof === C))
          Z = o.propTypes;
        else
          return;
        if (Z) {
          var B = ce(o);
          wn(Z, l.props, "prop", B, l);
        } else if (o.PropTypes !== void 0 && !Sn) {
          Sn = !0;
          var D = ce(o);
          p("Component %s declared `PropTypes` instead of `propTypes`. Did you misspell the property assignment?", D || "Unknown");
        }
        typeof o.getDefaultProps == "function" && !o.getDefaultProps.isReactClassApproved && p("getDefaultProps is only used on classic React.createClass definitions. Use a static property named `defaultProps` instead.");
      }
    }
    function Jc(l) {
      {
        for (var o = Object.keys(l.props), Z = 0; Z < o.length; Z++) {
          var B = o[Z];
          if (B !== "children" && B !== "key") {
            Ee(l), p("Invalid prop `%s` supplied to `React.Fragment`. React.Fragment can only have `key` and `children` props.", B), Ee(null);
            break;
          }
        }
        l.ref !== null && (Ee(l), p("Invalid attribute `ref` supplied to `React.Fragment`."), Ee(null));
      }
    }
    var pt = {};
    function Xt(l, o, Z, B, D, E) {
      {
        var j = ge(l);
        if (!j) {
          var w = "";
          (l === void 0 || typeof l == "object" && l !== null && Object.keys(l).length === 0) && (w += " You likely forgot to export your component from the file it's defined in, or you might have mixed up default and named imports.");
          var oe = zc();
          oe ? w += oe : w += Gt();
          var K;
          l === null ? K = "null" : ke(l) ? K = "array" : l !== void 0 && l.$$typeof === n ? (K = "<" + (ce(l.type) || "Unknown") + " />", w = " Did you accidentally export a JSX literal instead of a component?") : K = typeof l, p("React.jsx: type is invalid -- expected a string (for built-in components) or a class/function (for composite components) but got: %s.%s", K, w);
        }
        var ee = Bc(l, o, Z, D, E);
        if (ee == null)
          return ee;
        if (j) {
          var fe = o.children;
          if (fe !== void 0)
            if (B)
              if (ke(fe)) {
                for (var Ue = 0; Ue < fe.length; Ue++)
                  Wt(fe[Ue], l);
                Object.freeze && Object.freeze(fe);
              } else
                p("React.jsx: Static children should always be an array. You are likely explicitly calling React.jsxs or React.jsxDEV. Use the Babel transform instead.");
            else
              Wt(fe, l);
        }
        if (he.call(o, "key")) {
          var Fe = ce(l), se = Object.keys(o).filter(function(Dc) {
            return Dc !== "key";
          }), Dn = se.length > 0 ? "{key: someKey, " + se.join(": ..., ") + ": ...}" : "{key: someKey}";
          if (!pt[Fe + Dn]) {
            var Pc = se.length > 0 ? "{" + se.join(": ..., ") + ": ...}" : "{}";
            p(`A props object containing a "key" prop is being spread into JSX:
  let props = %s;
  <%s {...props} />
React keys must be passed directly to JSX without using spread:
  let props = %s;
  <%s key={someKey} {...props} />`, Dn, Fe, Pc, Fe), pt[Fe + Dn] = !0;
          }
        }
        return l === c ? Jc(ee) : Lc(ee), ee;
      }
    }
    function wc(l, o, Z) {
      return Xt(l, o, Z, !0);
    }
    function jc(l, o, Z) {
      return Xt(l, o, Z, !1);
    }
    var Fc = jc, Sc = wc;
    gn.Fragment = c, gn.jsx = Fc, gn.jsxs = Sc;
  }()), gn;
}
process.env.NODE_ENV === "production" ? Qn.exports = Uc() : Qn.exports = Hc();
var Xn = Qn.exports;
function Qc(e) {
  if (e.sheet)
    return e.sheet;
  for (var n = 0; n < document.styleSheets.length; n++)
    if (document.styleSheets[n].ownerNode === e)
      return document.styleSheets[n];
}
function _c(e) {
  var n = document.createElement("style");
  return n.setAttribute("data-emotion", e.key), e.nonce !== void 0 && n.setAttribute("nonce", e.nonce), n.appendChild(document.createTextNode("")), n.setAttribute("data-s", ""), n;
}
var $c = /* @__PURE__ */ function() {
  function e(t) {
    var c = this;
    this._insertTag = function(g) {
      var r;
      c.tags.length === 0 ? c.insertionPoint ? r = c.insertionPoint.nextSibling : c.prepend ? r = c.container.firstChild : r = c.before : r = c.tags[c.tags.length - 1].nextSibling, c.container.insertBefore(g, r), c.tags.push(g);
    }, this.isSpeedy = t.speedy === void 0 ? !0 : t.speedy, this.tags = [], this.ctr = 0, this.nonce = t.nonce, this.key = t.key, this.container = t.container, this.prepend = t.prepend, this.insertionPoint = t.insertionPoint, this.before = null;
  }
  var n = e.prototype;
  return n.hydrate = function(c) {
    c.forEach(this._insertTag);
  }, n.insert = function(c) {
    this.ctr % (this.isSpeedy ? 65e3 : 1) === 0 && this._insertTag(_c(this));
    var g = this.tags[this.tags.length - 1];
    if (this.isSpeedy) {
      var r = Qc(g);
      try {
        r.insertRule(c, r.cssRules.length);
      } catch {
      }
    } else
      g.appendChild(document.createTextNode(c));
    this.ctr++;
  }, n.flush = function() {
    this.tags.forEach(function(c) {
      var g;
      return (g = c.parentNode) == null ? void 0 : g.removeChild(c);
    }), this.tags = [], this.ctr = 0;
  }, e;
}(), Ie = "-ms-", xn = "-moz-", S = "-webkit-", kt = "comm", rt = "rule", it = "decl", Kc = "@import", Et = "@keyframes", qc = "@layer", el = Math.abs, hn = String.fromCharCode, nl = Object.assign;
function tl(e, n) {
  return ie(e, 0) ^ 45 ? (((n << 2 ^ ie(e, 0)) << 2 ^ ie(e, 1)) << 2 ^ ie(e, 2)) << 2 ^ ie(e, 3) : 0;
}
function Ut(e) {
  return e.trim();
}
function cl(e, n) {
  return (e = n.exec(e)) ? e[0] : e;
}
function P(e, n, t) {
  return e.replace(n, t);
}
function _n(e, n) {
  return e.indexOf(n);
}
function ie(e, n) {
  return e.charCodeAt(n) | 0;
}
function Cn(e, n, t) {
  return e.slice(n, t);
}
function Ye(e) {
  return e.length;
}
function It(e) {
  return e.length;
}
function mn(e, n) {
  return n.push(e), e;
}
function ll(e, n) {
  return e.map(n).join("");
}
var Yn = 1, tn = 1, Ht = 0, de = 0, ne = 0, cn = "";
function Nn(e, n, t, c, g, r, i) {
  return { value: e, root: n, parent: t, type: c, props: g, children: r, line: Yn, column: tn, length: i, return: "" };
}
function rn(e, n) {
  return nl(Nn("", null, null, "", null, null, 0), e, { length: -e.length }, n);
}
function gl() {
  return ne;
}
function rl() {
  return ne = de > 0 ? ie(cn, --de) : 0, tn--, ne === 10 && (tn = 1, Yn--), ne;
}
function Ge() {
  return ne = de < Ht ? ie(cn, de++) : 0, tn++, ne === 10 && (tn = 1, Yn++), ne;
}
function ze() {
  return ie(cn, de);
}
function fn() {
  return de;
}
function dn(e, n) {
  return Cn(cn, e, n);
}
function un(e) {
  switch (e) {
    case 0:
    case 9:
    case 10:
    case 13:
    case 32:
      return 5;
    case 33:
    case 43:
    case 44:
    case 47:
    case 62:
    case 64:
    case 126:
    case 59:
    case 123:
    case 125:
      return 4;
    case 58:
      return 3;
    case 34:
    case 39:
    case 40:
    case 91:
      return 2;
    case 41:
    case 93:
      return 1;
  }
  return 0;
}
function Qt(e) {
  return Yn = tn = 1, Ht = Ye(cn = e), de = 0, [];
}
function _t(e) {
  return cn = "", e;
}
function yn(e) {
  return Ut(dn(de - 1, $n(e === 91 ? e + 2 : e === 40 ? e + 1 : e)));
}
function il(e) {
  for (; (ne = ze()) && ne < 33; )
    Ge();
  return un(e) > 2 || un(ne) > 3 ? "" : " ";
}
function Il(e, n) {
  for (; --n && Ge() && !(ne < 48 || ne > 102 || ne > 57 && ne < 65 || ne > 70 && ne < 97); )
    ;
  return dn(e, fn() + (n < 6 && ze() == 32 && Ge() == 32));
}
function $n(e) {
  for (; Ge(); )
    switch (ne) {
      case e:
        return de;
      case 34:
      case 39:
        e !== 34 && e !== 39 && $n(ne);
        break;
      case 40:
        e === 41 && $n(e);
        break;
      case 92:
        Ge();
        break;
    }
  return de;
}
function al(e, n) {
  for (; Ge() && e + ne !== 57; )
    if (e + ne === 84 && ze() === 47)
      break;
  return "/*" + dn(n, de - 1) + "*" + hn(e === 47 ? e : Ge());
}
function ol(e) {
  for (; !un(ze()); )
    Ge();
  return dn(e, de);
}
function Cl(e) {
  return _t(Wn("", null, null, null, [""], e = Qt(e), 0, [0], e));
}
function Wn(e, n, t, c, g, r, i, I, a) {
  for (var s = 0, b = 0, C = i, u = 0, W = 0, d = 0, x = 1, v = 1, m = 1, p = 0, h = "", L = g, A = r, z = c, f = h; v; )
    switch (d = p, p = Ge()) {
      case 40:
        if (d != 108 && ie(f, C - 1) == 58) {
          _n(f += P(yn(p), "&", "&\f"), "&\f") != -1 && (m = -1);
          break;
        }
      case 34:
      case 39:
      case 91:
        f += yn(p);
        break;
      case 9:
      case 10:
      case 13:
      case 32:
        f += il(d);
        break;
      case 92:
        f += Il(fn() - 1, 7);
        continue;
      case 47:
        switch (ze()) {
          case 42:
          case 47:
            mn(ul(al(Ge(), fn()), n, t), a);
            break;
          default:
            f += "/";
        }
        break;
      case 123 * x:
        I[s++] = Ye(f) * m;
      case 125 * x:
      case 59:
      case 0:
        switch (p) {
          case 0:
          case 125:
            v = 0;
          case 59 + b:
            m == -1 && (f = P(f, /\f/g, "")), W > 0 && Ye(f) - C && mn(W > 32 ? ht(f + ";", c, t, C - 1) : ht(P(f, " ", "") + ";", c, t, C - 2), a);
            break;
          case 59:
            f += ";";
          default:
            if (mn(z = Vt(f, n, t, s, b, g, I, h, L = [], A = [], C), r), p === 123)
              if (b === 0)
                Wn(f, n, z, z, L, r, C, I, A);
              else
                switch (u === 99 && ie(f, 3) === 110 ? 100 : u) {
                  case 100:
                  case 108:
                  case 109:
                  case 115:
                    Wn(e, z, z, c && mn(Vt(e, z, z, 0, 0, g, I, h, g, L = [], C), A), g, A, C, I, c ? L : A);
                    break;
                  default:
                    Wn(f, z, z, z, [""], A, 0, I, A);
                }
        }
        s = b = W = 0, x = m = 1, h = f = "", C = i;
        break;
      case 58:
        C = 1 + Ye(f), W = d;
      default:
        if (x < 1) {
          if (p == 123)
            --x;
          else if (p == 125 && x++ == 0 && rl() == 125)
            continue;
        }
        switch (f += hn(p), p * x) {
          case 38:
            m = b > 0 ? 1 : (f += "\f", -1);
            break;
          case 44:
            I[s++] = (Ye(f) - 1) * m, m = 1;
            break;
          case 64:
            ze() === 45 && (f += yn(Ge())), u = ze(), b = C = Ye(h = f += ol(fn())), p++;
            break;
          case 45:
            d === 45 && Ye(f) == 2 && (x = 0);
        }
    }
  return r;
}
function Vt(e, n, t, c, g, r, i, I, a, s, b) {
  for (var C = g - 1, u = g === 0 ? r : [""], W = It(u), d = 0, x = 0, v = 0; d < c; ++d)
    for (var m = 0, p = Cn(e, C + 1, C = el(x = i[d])), h = e; m < W; ++m)
      (h = Ut(x > 0 ? u[m] + " " + p : P(p, /&\f/g, u[m]))) && (a[v++] = h);
  return Nn(e, n, t, g === 0 ? rt : I, a, s, b);
}
function ul(e, n, t) {
  return Nn(e, n, t, kt, hn(gl()), Cn(e, 2, -2), 0);
}
function ht(e, n, t, c) {
  return Nn(e, n, t, it, Cn(e, 0, c), Cn(e, c + 1, -1), c);
}
function qe(e, n) {
  for (var t = "", c = It(e), g = 0; g < c; g++)
    t += n(e[g], g, e, n) || "";
  return t;
}
function sl(e, n, t, c) {
  switch (e.type) {
    case qc:
      if (e.children.length) break;
    case Kc:
    case it:
      return e.return = e.return || e.value;
    case kt:
      return "";
    case Et:
      return e.return = e.value + "{" + qe(e.children, c) + "}";
    case rt:
      e.value = e.props.join(",");
  }
  return Ye(t = qe(e.children, c)) ? e.return = e.value + "{" + t + "}" : "";
}
function Al(e) {
  var n = It(e);
  return function(t, c, g, r) {
    for (var i = "", I = 0; I < n; I++)
      i += e[I](t, c, g, r) || "";
    return i;
  };
}
function bl(e) {
  return function(n) {
    n.root || (n = n.return) && e(n);
  };
}
function dl(e) {
  var n = /* @__PURE__ */ Object.create(null);
  return function(t) {
    return n[t] === void 0 && (n[t] = e(t)), n[t];
  };
}
var ml = function(n, t, c) {
  for (var g = 0, r = 0; g = r, r = ze(), g === 38 && r === 12 && (t[c] = 1), !un(r); )
    Ge();
  return dn(n, de);
}, Zl = function(n, t) {
  var c = -1, g = 44;
  do
    switch (un(g)) {
      case 0:
        g === 38 && ze() === 12 && (t[c] = 1), n[c] += ml(de - 1, t, c);
        break;
      case 2:
        n[c] += yn(g);
        break;
      case 4:
        if (g === 44) {
          n[++c] = ze() === 58 ? "&\f" : "", t[c] = n[c].length;
          break;
        }
      default:
        n[c] += hn(g);
    }
  while (g = Ge());
  return n;
}, Gl = function(n, t) {
  return _t(Zl(Qt(n), t));
}, Yt = /* @__PURE__ */ new WeakMap(), fl = function(n) {
  if (!(n.type !== "rule" || !n.parent || // positive .length indicates that this rule contains pseudo
  // negative .length indicates that this rule has been already prefixed
  n.length < 1)) {
    for (var t = n.value, c = n.parent, g = n.column === c.column && n.line === c.line; c.type !== "rule"; )
      if (c = c.parent, !c) return;
    if (!(n.props.length === 1 && t.charCodeAt(0) !== 58 && !Yt.get(c)) && !g) {
      Yt.set(n, !0);
      for (var r = [], i = Gl(t, r), I = c.props, a = 0, s = 0; a < i.length; a++)
        for (var b = 0; b < I.length; b++, s++)
          n.props[s] = r[a] ? i[a].replace(/&\f/g, I[b]) : I[b] + " " + i[a];
    }
  }
}, yl = function(n) {
  if (n.type === "decl") {
    var t = n.value;
    // charcode for l
    t.charCodeAt(0) === 108 && // charcode for b
    t.charCodeAt(2) === 98 && (n.return = "", n.value = "");
  }
};
function $t(e, n) {
  switch (tl(e, n)) {
    case 5103:
      return S + "print-" + e + e;
    case 5737:
    case 4201:
    case 3177:
    case 3433:
    case 1641:
    case 4457:
    case 2921:
    case 5572:
    case 6356:
    case 5844:
    case 3191:
    case 6645:
    case 3005:
    case 6391:
    case 5879:
    case 5623:
    case 6135:
    case 4599:
    case 4855:
    case 4215:
    case 6389:
    case 5109:
    case 5365:
    case 5621:
    case 3829:
      return S + e + e;
    case 5349:
    case 4246:
    case 4810:
    case 6968:
    case 2756:
      return S + e + xn + e + Ie + e + e;
    case 6828:
    case 4268:
      return S + e + Ie + e + e;
    case 6165:
      return S + e + Ie + "flex-" + e + e;
    case 5187:
      return S + e + P(e, /(\w+).+(:[^]+)/, S + "box-$1$2" + Ie + "flex-$1$2") + e;
    case 5443:
      return S + e + Ie + "flex-item-" + P(e, /flex-|-self/, "") + e;
    case 4675:
      return S + e + Ie + "flex-line-pack" + P(e, /align-content|flex-|-self/, "") + e;
    case 5548:
      return S + e + Ie + P(e, "shrink", "negative") + e;
    case 5292:
      return S + e + Ie + P(e, "basis", "preferred-size") + e;
    case 6060:
      return S + "box-" + P(e, "-grow", "") + S + e + Ie + P(e, "grow", "positive") + e;
    case 4554:
      return S + P(e, /([^-])(transform)/g, "$1" + S + "$2") + e;
    case 6187:
      return P(P(P(e, /(zoom-|grab)/, S + "$1"), /(image-set)/, S + "$1"), e, "") + e;
    case 5495:
    case 3959:
      return P(e, /(image-set\([^]*)/, S + "$1$`$1");
    case 4968:
      return P(P(e, /(.+:)(flex-)?(.*)/, S + "box-pack:$3" + Ie + "flex-pack:$3"), /s.+-b[^;]+/, "justify") + S + e + e;
    case 4095:
    case 3583:
    case 4068:
    case 2532:
      return P(e, /(.+)-inline(.+)/, S + "$1$2") + e;
    case 8116:
    case 7059:
    case 5753:
    case 5535:
    case 5445:
    case 5701:
    case 4933:
    case 4677:
    case 5533:
    case 5789:
    case 5021:
    case 4765:
      if (Ye(e) - 1 - n > 6) switch (ie(e, n + 1)) {
        case 109:
          if (ie(e, n + 4) !== 45) break;
        case 102:
          return P(e, /(.+:)(.+)-([^]+)/, "$1" + S + "$2-$3$1" + xn + (ie(e, n + 3) == 108 ? "$3" : "$2-$3")) + e;
        case 115:
          return ~_n(e, "stretch") ? $t(P(e, "stretch", "fill-available"), n) + e : e;
      }
      break;
    case 4949:
      if (ie(e, n + 1) !== 115) break;
    case 6444:
      switch (ie(e, Ye(e) - 3 - (~_n(e, "!important") && 10))) {
        case 107:
          return P(e, ":", ":" + S) + e;
        case 101:
          return P(e, /(.+:)([^;!]+)(;|!.+)?/, "$1" + S + (ie(e, 14) === 45 ? "inline-" : "") + "box$3$1" + S + "$2$3$1" + Ie + "$2box$3") + e;
      }
      break;
    case 5936:
      switch (ie(e, n + 11)) {
        case 114:
          return S + e + Ie + P(e, /[svh]\w+-[tblr]{2}/, "tb") + e;
        case 108:
          return S + e + Ie + P(e, /[svh]\w+-[tblr]{2}/, "tb-rl") + e;
        case 45:
          return S + e + Ie + P(e, /[svh]\w+-[tblr]{2}/, "lr") + e;
      }
      return S + e + Ie + e + e;
  }
  return e;
}
var Wl = function(n, t, c, g) {
  if (n.length > -1 && !n.return) switch (n.type) {
    case it:
      n.return = $t(n.value, n.length);
      break;
    case Et:
      return qe([rn(n, {
        value: P(n.value, "@", "@" + S)
      })], g);
    case rt:
      if (n.length) return ll(n.props, function(r) {
        switch (cl(r, /(::plac\w+|:read-\w+)/)) {
          case ":read-only":
          case ":read-write":
            return qe([rn(n, {
              props: [P(r, /:(read-\w+)/, ":" + xn + "$1")]
            })], g);
          case "::placeholder":
            return qe([rn(n, {
              props: [P(r, /:(plac\w+)/, ":" + S + "input-$1")]
            }), rn(n, {
              props: [P(r, /:(plac\w+)/, ":" + xn + "$1")]
            }), rn(n, {
              props: [P(r, /:(plac\w+)/, Ie + "input-$1")]
            })], g);
        }
        return "";
      });
  }
}, pl = [Wl], Xl = function(n) {
  var t = n.key;
  if (t === "css") {
    var c = document.querySelectorAll("style[data-emotion]:not([data-s])");
    Array.prototype.forEach.call(c, function(x) {
      var v = x.getAttribute("data-emotion");
      v.indexOf(" ") !== -1 && (document.head.appendChild(x), x.setAttribute("data-s", ""));
    });
  }
  var g = n.stylisPlugins || pl, r = {}, i, I = [];
  i = n.container || document.head, Array.prototype.forEach.call(
    // this means we will ignore elements which don't have a space in them which
    // means that the style elements we're looking at are only Emotion 11 server-rendered style elements
    document.querySelectorAll('style[data-emotion^="' + t + ' "]'),
    function(x) {
      for (var v = x.getAttribute("data-emotion").split(" "), m = 1; m < v.length; m++)
        r[v[m]] = !0;
      I.push(x);
    }
  );
  var a, s = [fl, yl];
  {
    var b, C = [sl, bl(function(x) {
      b.insert(x);
    })], u = Al(s.concat(g, C)), W = function(v) {
      return qe(Cl(v), u);
    };
    a = function(v, m, p, h) {
      b = p, W(v ? v + "{" + m.styles + "}" : m.styles), h && (d.inserted[m.name] = !0);
    };
  }
  var d = {
    key: t,
    sheet: new $c({
      key: t,
      container: i,
      nonce: n.nonce,
      speedy: n.speedy,
      prepend: n.prepend,
      insertionPoint: n.insertionPoint
    }),
    nonce: n.nonce,
    inserted: r,
    registered: {},
    insert: a
  };
  return d.sheet.hydrate(I), d;
}, Kn = { exports: {} }, O = {};
/** @license React v16.13.1
 * react-is.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var Nt;
function xl() {
  if (Nt) return O;
  Nt = 1;
  var e = typeof Symbol == "function" && Symbol.for, n = e ? Symbol.for("react.element") : 60103, t = e ? Symbol.for("react.portal") : 60106, c = e ? Symbol.for("react.fragment") : 60107, g = e ? Symbol.for("react.strict_mode") : 60108, r = e ? Symbol.for("react.profiler") : 60114, i = e ? Symbol.for("react.provider") : 60109, I = e ? Symbol.for("react.context") : 60110, a = e ? Symbol.for("react.async_mode") : 60111, s = e ? Symbol.for("react.concurrent_mode") : 60111, b = e ? Symbol.for("react.forward_ref") : 60112, C = e ? Symbol.for("react.suspense") : 60113, u = e ? Symbol.for("react.suspense_list") : 60120, W = e ? Symbol.for("react.memo") : 60115, d = e ? Symbol.for("react.lazy") : 60116, x = e ? Symbol.for("react.block") : 60121, v = e ? Symbol.for("react.fundamental") : 60117, m = e ? Symbol.for("react.responder") : 60118, p = e ? Symbol.for("react.scope") : 60119;
  function h(A) {
    if (typeof A == "object" && A !== null) {
      var z = A.$$typeof;
      switch (z) {
        case n:
          switch (A = A.type, A) {
            case a:
            case s:
            case c:
            case r:
            case g:
            case C:
              return A;
            default:
              switch (A = A && A.$$typeof, A) {
                case I:
                case b:
                case d:
                case W:
                case i:
                  return A;
                default:
                  return z;
              }
          }
        case t:
          return z;
      }
    }
  }
  function L(A) {
    return h(A) === s;
  }
  return O.AsyncMode = a, O.ConcurrentMode = s, O.ContextConsumer = I, O.ContextProvider = i, O.Element = n, O.ForwardRef = b, O.Fragment = c, O.Lazy = d, O.Memo = W, O.Portal = t, O.Profiler = r, O.StrictMode = g, O.Suspense = C, O.isAsyncMode = function(A) {
    return L(A) || h(A) === a;
  }, O.isConcurrentMode = L, O.isContextConsumer = function(A) {
    return h(A) === I;
  }, O.isContextProvider = function(A) {
    return h(A) === i;
  }, O.isElement = function(A) {
    return typeof A == "object" && A !== null && A.$$typeof === n;
  }, O.isForwardRef = function(A) {
    return h(A) === b;
  }, O.isFragment = function(A) {
    return h(A) === c;
  }, O.isLazy = function(A) {
    return h(A) === d;
  }, O.isMemo = function(A) {
    return h(A) === W;
  }, O.isPortal = function(A) {
    return h(A) === t;
  }, O.isProfiler = function(A) {
    return h(A) === r;
  }, O.isStrictMode = function(A) {
    return h(A) === g;
  }, O.isSuspense = function(A) {
    return h(A) === C;
  }, O.isValidElementType = function(A) {
    return typeof A == "string" || typeof A == "function" || A === c || A === s || A === r || A === g || A === C || A === u || typeof A == "object" && A !== null && (A.$$typeof === d || A.$$typeof === W || A.$$typeof === i || A.$$typeof === I || A.$$typeof === b || A.$$typeof === v || A.$$typeof === m || A.$$typeof === p || A.$$typeof === x);
  }, O.typeOf = h, O;
}
var T = {};
/** @license React v16.13.1
 * react-is.development.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var Bt;
function vl() {
  return Bt || (Bt = 1, process.env.NODE_ENV !== "production" && function() {
    var e = typeof Symbol == "function" && Symbol.for, n = e ? Symbol.for("react.element") : 60103, t = e ? Symbol.for("react.portal") : 60106, c = e ? Symbol.for("react.fragment") : 60107, g = e ? Symbol.for("react.strict_mode") : 60108, r = e ? Symbol.for("react.profiler") : 60114, i = e ? Symbol.for("react.provider") : 60109, I = e ? Symbol.for("react.context") : 60110, a = e ? Symbol.for("react.async_mode") : 60111, s = e ? Symbol.for("react.concurrent_mode") : 60111, b = e ? Symbol.for("react.forward_ref") : 60112, C = e ? Symbol.for("react.suspense") : 60113, u = e ? Symbol.for("react.suspense_list") : 60120, W = e ? Symbol.for("react.memo") : 60115, d = e ? Symbol.for("react.lazy") : 60116, x = e ? Symbol.for("react.block") : 60121, v = e ? Symbol.for("react.fundamental") : 60117, m = e ? Symbol.for("react.responder") : 60118, p = e ? Symbol.for("react.scope") : 60119;
    function h(G) {
      return typeof G == "string" || typeof G == "function" || // Note: its typeof might be other than 'symbol' or 'number' if it's a polyfill.
      G === c || G === s || G === r || G === g || G === C || G === u || typeof G == "object" && G !== null && (G.$$typeof === d || G.$$typeof === W || G.$$typeof === i || G.$$typeof === I || G.$$typeof === b || G.$$typeof === v || G.$$typeof === m || G.$$typeof === p || G.$$typeof === x);
    }
    function L(G) {
      if (typeof G == "object" && G !== null) {
        var M = G.$$typeof;
        switch (M) {
          case n:
            var le = G.type;
            switch (le) {
              case a:
              case s:
              case c:
              case r:
              case g:
              case C:
                return le;
              default:
                var me = le && le.$$typeof;
                switch (me) {
                  case I:
                  case b:
                  case d:
                  case W:
                  case i:
                    return me;
                  default:
                    return M;
                }
            }
          case t:
            return M;
        }
      }
    }
    var A = a, z = s, f = I, ae = i, Ce = n, ge = b, te = c, U = d, ce = W, H = t, Q = r, q = g, xe = C, ye = !1;
    function ve(G) {
      return ye || (ye = !0, console.warn("The ReactIs.isAsyncMode() alias has been deprecated, and will be removed in React 17+. Update your code to use ReactIs.isConcurrentMode() instead. It has the exact same API.")), Re(G) || L(G) === a;
    }
    function Re(G) {
      return L(G) === s;
    }
    function We(G) {
      return L(G) === I;
    }
    function Ve(G) {
      return L(G) === i;
    }
    function y(G) {
      return typeof G == "object" && G !== null && G.$$typeof === n;
    }
    function Y(G) {
      return L(G) === b;
    }
    function R(G) {
      return L(G) === c;
    }
    function V(G) {
      return L(G) === d;
    }
    function X(G) {
      return L(G) === W;
    }
    function N(G) {
      return L(G) === t;
    }
    function F(G) {
      return L(G) === r;
    }
    function k(G) {
      return L(G) === g;
    }
    function ue(G) {
      return L(G) === C;
    }
    T.AsyncMode = A, T.ConcurrentMode = z, T.ContextConsumer = f, T.ContextProvider = ae, T.Element = Ce, T.ForwardRef = ge, T.Fragment = te, T.Lazy = U, T.Memo = ce, T.Portal = H, T.Profiler = Q, T.StrictMode = q, T.Suspense = xe, T.isAsyncMode = ve, T.isConcurrentMode = Re, T.isContextConsumer = We, T.isContextProvider = Ve, T.isElement = y, T.isForwardRef = Y, T.isFragment = R, T.isLazy = V, T.isMemo = X, T.isPortal = N, T.isProfiler = F, T.isStrictMode = k, T.isSuspense = ue, T.isValidElementType = h, T.typeOf = L;
  }()), T;
}
process.env.NODE_ENV === "production" ? Kn.exports = xl() : Kn.exports = vl();
var Vl = Kn.exports, Kt = Vl, hl = {
  $$typeof: !0,
  render: !0,
  defaultProps: !0,
  displayName: !0,
  propTypes: !0
}, Yl = {
  $$typeof: !0,
  compare: !0,
  defaultProps: !0,
  displayName: !0,
  propTypes: !0,
  type: !0
}, qt = {};
qt[Kt.ForwardRef] = hl;
qt[Kt.Memo] = Yl;
var Nl = !0;
function Bl(e, n, t) {
  var c = "";
  return t.split(" ").forEach(function(g) {
    e[g] !== void 0 ? n.push(e[g] + ";") : g && (c += g + " ");
  }), c;
}
var ec = function(n, t, c) {
  var g = n.key + "-" + t.name;
  // we only need to add the styles to the registered cache if the
  // class name could be used further down
  // the tree but if it's a string tag, we know it won't
  // so we don't have to add it to registered cache.
  // this improves memory usage since we can avoid storing the whole style string
  (c === !1 || // we need to always store it if we're in compat mode and
  // in node since emotion-server relies on whether a style is in
  // the registered cache to know whether a style is global or not
  // also, note that this check will be dead code eliminated in the browser
  Nl === !1) && n.registered[g] === void 0 && (n.registered[g] = t.styles);
}, zl = function(n, t, c) {
  ec(n, t, c);
  var g = n.key + "-" + t.name;
  if (n.inserted[t.name] === void 0) {
    var r = t;
    do
      n.insert(t === r ? "." + g : "", r, n.sheet, !0), r = r.next;
    while (r !== void 0);
  }
};
function Rl(e) {
  for (var n = 0, t, c = 0, g = e.length; g >= 4; ++c, g -= 4)
    t = e.charCodeAt(c) & 255 | (e.charCodeAt(++c) & 255) << 8 | (e.charCodeAt(++c) & 255) << 16 | (e.charCodeAt(++c) & 255) << 24, t = /* Math.imul(k, m): */
    (t & 65535) * 1540483477 + ((t >>> 16) * 59797 << 16), t ^= /* k >>> r: */
    t >>> 24, n = /* Math.imul(k, m): */
    (t & 65535) * 1540483477 + ((t >>> 16) * 59797 << 16) ^ /* Math.imul(h, m): */
    (n & 65535) * 1540483477 + ((n >>> 16) * 59797 << 16);
  switch (g) {
    case 3:
      n ^= (e.charCodeAt(c + 2) & 255) << 16;
    case 2:
      n ^= (e.charCodeAt(c + 1) & 255) << 8;
    case 1:
      n ^= e.charCodeAt(c) & 255, n = /* Math.imul(h, m): */
      (n & 65535) * 1540483477 + ((n >>> 16) * 59797 << 16);
  }
  return n ^= n >>> 13, n = /* Math.imul(h, m): */
  (n & 65535) * 1540483477 + ((n >>> 16) * 59797 << 16), ((n ^ n >>> 15) >>> 0).toString(36);
}
var Ll = {
  animationIterationCount: 1,
  aspectRatio: 1,
  borderImageOutset: 1,
  borderImageSlice: 1,
  borderImageWidth: 1,
  boxFlex: 1,
  boxFlexGroup: 1,
  boxOrdinalGroup: 1,
  columnCount: 1,
  columns: 1,
  flex: 1,
  flexGrow: 1,
  flexPositive: 1,
  flexShrink: 1,
  flexNegative: 1,
  flexOrder: 1,
  gridRow: 1,
  gridRowEnd: 1,
  gridRowSpan: 1,
  gridRowStart: 1,
  gridColumn: 1,
  gridColumnEnd: 1,
  gridColumnSpan: 1,
  gridColumnStart: 1,
  msGridRow: 1,
  msGridRowSpan: 1,
  msGridColumn: 1,
  msGridColumnSpan: 1,
  fontWeight: 1,
  lineHeight: 1,
  opacity: 1,
  order: 1,
  orphans: 1,
  scale: 1,
  tabSize: 1,
  widows: 1,
  zIndex: 1,
  zoom: 1,
  WebkitLineClamp: 1,
  // SVG-related properties
  fillOpacity: 1,
  floodOpacity: 1,
  stopOpacity: 1,
  strokeDasharray: 1,
  strokeDashoffset: 1,
  strokeMiterlimit: 1,
  strokeOpacity: 1,
  strokeWidth: 1
}, Jl = /[A-Z]|^ms/g, wl = /_EMO_([^_]+?)_([^]*?)_EMO_/g, nc = function(n) {
  return n.charCodeAt(1) === 45;
}, zt = function(n) {
  return n != null && typeof n != "boolean";
}, On = /* @__PURE__ */ dl(function(e) {
  return nc(e) ? e : e.replace(Jl, "-$&").toLowerCase();
}), Rt = function(n, t) {
  switch (n) {
    case "animation":
    case "animationName":
      if (typeof t == "string")
        return t.replace(wl, function(c, g, r) {
          return Ne = {
            name: g,
            styles: r,
            next: Ne
          }, g;
        });
  }
  return Ll[n] !== 1 && !nc(n) && typeof t == "number" && t !== 0 ? t + "px" : t;
};
function sn(e, n, t) {
  if (t == null)
    return "";
  var c = t;
  if (c.__emotion_styles !== void 0)
    return c;
  switch (typeof t) {
    case "boolean":
      return "";
    case "object": {
      var g = t;
      if (g.anim === 1)
        return Ne = {
          name: g.name,
          styles: g.styles,
          next: Ne
        }, g.name;
      var r = t;
      if (r.styles !== void 0) {
        var i = r.next;
        if (i !== void 0)
          for (; i !== void 0; )
            Ne = {
              name: i.name,
              styles: i.styles,
              next: Ne
            }, i = i.next;
        var I = r.styles + ";";
        return I;
      }
      return jl(e, n, t);
    }
    case "function": {
      if (e !== void 0) {
        var a = Ne, s = t(e);
        return Ne = a, sn(e, n, s);
      }
      break;
    }
  }
  var b = t;
  return b;
}
function jl(e, n, t) {
  var c = "";
  if (Array.isArray(t))
    for (var g = 0; g < t.length; g++)
      c += sn(e, n, t[g]) + ";";
  else
    for (var r in t) {
      var i = t[r];
      if (typeof i != "object") {
        var I = i;
        zt(I) && (c += On(r) + ":" + Rt(r, I) + ";");
      } else if (Array.isArray(i) && typeof i[0] == "string" && n == null)
        for (var a = 0; a < i.length; a++)
          zt(i[a]) && (c += On(r) + ":" + Rt(r, i[a]) + ";");
      else {
        var s = sn(e, n, i);
        switch (r) {
          case "animation":
          case "animationName": {
            c += On(r) + ":" + s + ";";
            break;
          }
          default:
            c += r + "{" + s + "}";
        }
      }
    }
  return c;
}
var Lt = /label:\s*([^\s;{]+)\s*(;|$)/g, Ne;
function Fl(e, n, t) {
  if (e.length === 1 && typeof e[0] == "object" && e[0] !== null && e[0].styles !== void 0)
    return e[0];
  var c = !0, g = "";
  Ne = void 0;
  var r = e[0];
  if (r == null || r.raw === void 0)
    c = !1, g += sn(t, n, r);
  else {
    var i = r;
    g += i[0];
  }
  for (var I = 1; I < e.length; I++)
    if (g += sn(t, n, e[I]), c) {
      var a = r;
      g += a[I];
    }
  Lt.lastIndex = 0;
  for (var s = "", b; (b = Lt.exec(g)) !== null; )
    s += "-" + b[1];
  var C = Rl(g) + s;
  return {
    name: C,
    styles: g,
    next: Ne
  };
}
var Sl = function(n) {
  return n();
}, Pl = Be.useInsertionEffect ? Be.useInsertionEffect : !1, Dl = Pl || Sl, tc = /* @__PURE__ */ Be.createContext(
  // we're doing this to avoid preconstruct's dead code elimination in this one case
  // because this module is primarily intended for the browser and node
  // but it's also required in react native and similar environments sometimes
  // and we could have a special build just for that
  // but this is much easier and the native packages
  // might use a different theme context in the future anyway
  typeof HTMLElement < "u" ? /* @__PURE__ */ Xl({
    key: "css"
  }) : null
);
tc.Provider;
var Ol = function(n) {
  return /* @__PURE__ */ lt(function(t, c) {
    var g = gt(tc);
    return n(t, g, c);
  });
}, Tl = /* @__PURE__ */ Be.createContext({}), Bn = {}.hasOwnProperty, qn = "__EMOTION_TYPE_PLEASE_DO_NOT_USE__", cc = function(n, t) {
  var c = {};
  for (var g in t)
    Bn.call(t, g) && (c[g] = t[g]);
  return c[qn] = n, c;
}, Ml = function(n) {
  var t = n.cache, c = n.serialized, g = n.isStringTag;
  return ec(t, c, g), Dl(function() {
    return zl(t, c, g);
  }), null;
}, kl = /* @__PURE__ */ Ol(function(e, n, t) {
  var c = e.css;
  typeof c == "string" && n.registered[c] !== void 0 && (c = n.registered[c]);
  var g = e[qn], r = [c], i = "";
  typeof e.className == "string" ? i = Bl(n.registered, r, e.className) : e.className != null && (i = e.className + " ");
  var I = Fl(r, void 0, Be.useContext(Tl));
  i += n.key + "-" + I.name;
  var a = {};
  for (var s in e)
    Bn.call(e, s) && s !== "css" && s !== qn && (a[s] = e[s]);
  return a.className = i, t && (a.ref = t), /* @__PURE__ */ Be.createElement(Be.Fragment, null, /* @__PURE__ */ Be.createElement(Ml, {
    cache: n,
    serialized: I,
    isStringTag: typeof g == "string"
  }), /* @__PURE__ */ Be.createElement(g, a));
}), lc = kl, _ = function(n, t, c) {
  return Bn.call(t, "css") ? Xn.jsx(lc, cc(n, t), c) : Xn.jsx(n, t, c);
}, Zn = function(n, t, c) {
  return Bn.call(t, "css") ? Xn.jsxs(lc, cc(n, t), c) : Xn.jsxs(n, t, c);
};
const zn = Mc(null);
zn.displayName = "PanelGroupContext";
const $ = {
  group: "data-panel-group",
  groupDirection: "data-panel-group-direction",
  groupId: "data-panel-group-id",
  panel: "data-panel",
  panelCollapsible: "data-panel-collapsible",
  panelId: "data-panel-id",
  panelSize: "data-panel-size",
  resizeHandle: "data-resize-handle",
  resizeHandleActive: "data-resize-handle-active",
  resizeHandleEnabled: "data-panel-resize-handle-enabled",
  resizeHandleId: "data-panel-resize-handle-id",
  resizeHandleState: "data-resize-handle-state"
}, at = 10, Oe = kc, Jt = Be.useId, El = typeof Jt == "function" ? Jt : () => null;
let Ul = 0;
function ot(e = null) {
  const n = El(), t = be(e || n || null);
  return t.current === null && (t.current = "" + Ul++), e ?? t.current;
}
function gc({
  children: e,
  className: n = "",
  collapsedSize: t,
  collapsible: c,
  defaultSize: g,
  forwardedRef: r,
  id: i,
  maxSize: I,
  minSize: a,
  onCollapse: s,
  onExpand: b,
  onResize: C,
  order: u,
  style: W,
  tagName: d = "div",
  ...x
}) {
  const v = gt(zn);
  if (v === null)
    throw Error("Panel components must be rendered within a PanelGroup container");
  const {
    collapsePanel: m,
    expandPanel: p,
    getPanelSize: h,
    getPanelStyle: L,
    groupId: A,
    isPanelCollapsed: z,
    reevaluatePanelConstraints: f,
    registerPanel: ae,
    resizePanel: Ce,
    unregisterPanel: ge
  } = v, te = ot(i), U = be({
    callbacks: {
      onCollapse: s,
      onExpand: b,
      onResize: C
    },
    constraints: {
      collapsedSize: t,
      collapsible: c,
      defaultSize: g,
      maxSize: I,
      minSize: a
    },
    id: te,
    idIsFromProps: i !== void 0,
    order: u
  });
  be({
    didLogMissingDefaultSizeWarning: !1
  }), Oe(() => {
    const {
      callbacks: H,
      constraints: Q
    } = U.current, q = {
      ...Q
    };
    U.current.id = te, U.current.idIsFromProps = i !== void 0, U.current.order = u, H.onCollapse = s, H.onExpand = b, H.onResize = C, Q.collapsedSize = t, Q.collapsible = c, Q.defaultSize = g, Q.maxSize = I, Q.minSize = a, (q.collapsedSize !== Q.collapsedSize || q.collapsible !== Q.collapsible || q.maxSize !== Q.maxSize || q.minSize !== Q.minSize) && f(U.current, q);
  }), Oe(() => {
    const H = U.current;
    return ae(H), () => {
      ge(H);
    };
  }, [u, te, ae, ge]), Mt(r, () => ({
    collapse: () => {
      m(U.current);
    },
    expand: (H) => {
      p(U.current, H);
    },
    getId() {
      return te;
    },
    getSize() {
      return h(U.current);
    },
    isCollapsed() {
      return z(U.current);
    },
    isExpanded() {
      return !z(U.current);
    },
    resize: (H) => {
      Ce(U.current, H);
    }
  }), [m, p, h, z, te, Ce]);
  const ce = L(U.current, g);
  return nn(d, {
    ...x,
    children: e,
    className: n,
    id: te,
    style: {
      ...ce,
      ...W
    },
    // CSS selectors
    [$.groupId]: A,
    [$.panel]: "",
    [$.panelCollapsible]: c || void 0,
    [$.panelId]: te,
    [$.panelSize]: parseFloat("" + ce.flexGrow).toFixed(1)
  });
}
const In = lt((e, n) => nn(gc, {
  ...e,
  forwardedRef: n
}));
gc.displayName = "Panel";
In.displayName = "forwardRef(Panel)";
let et = null, pn = -1, Je = null;
function Hl(e, n) {
  if (n) {
    const t = (n & oc) !== 0, c = (n & Cc) !== 0, g = (n & uc) !== 0, r = (n & sc) !== 0;
    if (t)
      return g ? "se-resize" : r ? "ne-resize" : "e-resize";
    if (c)
      return g ? "sw-resize" : r ? "nw-resize" : "w-resize";
    if (g)
      return "s-resize";
    if (r)
      return "n-resize";
  }
  switch (e) {
    case "horizontal":
      return "ew-resize";
    case "intersection":
      return "move";
    case "vertical":
      return "ns-resize";
  }
}
function Ql() {
  Je !== null && (document.head.removeChild(Je), et = null, Je = null, pn = -1);
}
function Tn(e, n) {
  var t, c;
  const g = Hl(e, n);
  if (et !== g) {
    if (et = g, Je === null && (Je = document.createElement("style"), document.head.appendChild(Je)), pn >= 0) {
      var r;
      (r = Je.sheet) === null || r === void 0 || r.removeRule(pn);
    }
    pn = (t = (c = Je.sheet) === null || c === void 0 ? void 0 : c.insertRule(`*{cursor: ${g} !important;}`)) !== null && t !== void 0 ? t : -1;
  }
}
function rc(e) {
  return e.type === "keydown";
}
function ic(e) {
  return e.type.startsWith("pointer");
}
function Ic(e) {
  return e.type.startsWith("mouse");
}
function Rn(e) {
  if (ic(e)) {
    if (e.isPrimary)
      return {
        x: e.clientX,
        y: e.clientY
      };
  } else if (Ic(e))
    return {
      x: e.clientX,
      y: e.clientY
    };
  return {
    x: 1 / 0,
    y: 1 / 0
  };
}
function _l() {
  if (typeof matchMedia == "function")
    return matchMedia("(pointer:coarse)").matches ? "coarse" : "fine";
}
function $l(e, n, t) {
  return e.x < n.x + n.width && e.x + e.width > n.x && e.y < n.y + n.height && e.y + e.height > n.y;
}
function Kl(e, n) {
  if (e === n) throw new Error("Cannot compare node with itself");
  const t = {
    a: Ft(e),
    b: Ft(n)
  };
  let c;
  for (; t.a.at(-1) === t.b.at(-1); )
    e = t.a.pop(), n = t.b.pop(), c = e;
  J(c, "Stacking order can only be calculated for elements with a common ancestor");
  const g = {
    a: jt(wt(t.a)),
    b: jt(wt(t.b))
  };
  if (g.a === g.b) {
    const r = c.childNodes, i = {
      a: t.a.at(-1),
      b: t.b.at(-1)
    };
    let I = r.length;
    for (; I--; ) {
      const a = r[I];
      if (a === i.a) return 1;
      if (a === i.b) return -1;
    }
  }
  return Math.sign(g.a - g.b);
}
const ql = /\b(?:position|zIndex|opacity|transform|webkitTransform|mixBlendMode|filter|webkitFilter|isolation)\b/;
function eg(e) {
  var n;
  const t = getComputedStyle((n = ac(e)) !== null && n !== void 0 ? n : e).display;
  return t === "flex" || t === "inline-flex";
}
function ng(e) {
  const n = getComputedStyle(e);
  return !!(n.position === "fixed" || n.zIndex !== "auto" && (n.position !== "static" || eg(e)) || +n.opacity < 1 || "transform" in n && n.transform !== "none" || "webkitTransform" in n && n.webkitTransform !== "none" || "mixBlendMode" in n && n.mixBlendMode !== "normal" || "filter" in n && n.filter !== "none" || "webkitFilter" in n && n.webkitFilter !== "none" || "isolation" in n && n.isolation === "isolate" || ql.test(n.willChange) || n.webkitOverflowScrolling === "touch");
}
function wt(e) {
  let n = e.length;
  for (; n--; ) {
    const t = e[n];
    if (J(t, "Missing node"), ng(t)) return t;
  }
  return null;
}
function jt(e) {
  return e && Number(getComputedStyle(e).zIndex) || 0;
}
function Ft(e) {
  const n = [];
  for (; e; )
    n.push(e), e = ac(e);
  return n;
}
function ac(e) {
  const {
    parentNode: n
  } = e;
  return n && n instanceof ShadowRoot ? n.host : n;
}
const oc = 1, Cc = 2, uc = 4, sc = 8, tg = _l() === "coarse";
let pe = [], en = !1, Pe = /* @__PURE__ */ new Map(), Ln = /* @__PURE__ */ new Map();
const An = /* @__PURE__ */ new Set();
function cg(e, n, t, c, g) {
  var r;
  const {
    ownerDocument: i
  } = n, I = {
    direction: t,
    element: n,
    hitAreaMargins: c,
    setResizeHandlerState: g
  }, a = (r = Pe.get(i)) !== null && r !== void 0 ? r : 0;
  return Pe.set(i, a + 1), An.add(I), vn(), function() {
    var b;
    Ln.delete(e), An.delete(I);
    const C = (b = Pe.get(i)) !== null && b !== void 0 ? b : 1;
    if (Pe.set(i, C - 1), vn(), C === 1 && Pe.delete(i), pe.includes(I)) {
      const u = pe.indexOf(I);
      u >= 0 && pe.splice(u, 1), ut(), g("up", !0, null);
    }
  };
}
function lg(e) {
  const {
    target: n
  } = e, {
    x: t,
    y: c
  } = Rn(e);
  en = !0, Ct({
    target: n,
    x: t,
    y: c
  }), vn(), pe.length > 0 && (Vn("down", e), e.preventDefault(), Ac(n) || e.stopImmediatePropagation());
}
function Mn(e) {
  const {
    x: n,
    y: t
  } = Rn(e);
  if (en && e.buttons === 0 && (en = !1, Vn("up", e)), !en) {
    const {
      target: c
    } = e;
    Ct({
      target: c,
      x: n,
      y: t
    });
  }
  Vn("move", e), ut(), pe.length > 0 && e.preventDefault();
}
function kn(e) {
  const {
    target: n
  } = e, {
    x: t,
    y: c
  } = Rn(e);
  Ln.clear(), en = !1, pe.length > 0 && (e.preventDefault(), Ac(n) || e.stopImmediatePropagation()), Vn("up", e), Ct({
    target: n,
    x: t,
    y: c
  }), ut(), vn();
}
function Ac(e) {
  let n = e;
  for (; n; ) {
    if (n.hasAttribute($.resizeHandle))
      return !0;
    n = n.parentElement;
  }
  return !1;
}
function Ct({
  target: e,
  x: n,
  y: t
}) {
  pe.splice(0);
  let c = null;
  (e instanceof HTMLElement || e instanceof SVGElement) && (c = e), An.forEach((g) => {
    const {
      element: r,
      hitAreaMargins: i
    } = g, I = r.getBoundingClientRect(), {
      bottom: a,
      left: s,
      right: b,
      top: C
    } = I, u = tg ? i.coarse : i.fine;
    if (n >= s - u && n <= b + u && t >= C - u && t <= a + u) {
      if (c !== null && document.contains(c) && r !== c && !r.contains(c) && !c.contains(r) && // Calculating stacking order has a cost, so we should avoid it if possible
      // That is why we only check potentially intersecting handles,
      // and why we skip if the event target is within the handle's DOM
      Kl(c, r) > 0) {
        let d = c, x = !1;
        for (; d && !d.contains(r); ) {
          if ($l(d.getBoundingClientRect(), I)) {
            x = !0;
            break;
          }
          d = d.parentElement;
        }
        if (x)
          return;
      }
      pe.push(g);
    }
  });
}
function En(e, n) {
  Ln.set(e, n);
}
function ut() {
  let e = !1, n = !1;
  pe.forEach((c) => {
    const {
      direction: g
    } = c;
    g === "horizontal" ? e = !0 : n = !0;
  });
  let t = 0;
  Ln.forEach((c) => {
    t |= c;
  }), e && n ? Tn("intersection", t) : e ? Tn("horizontal", t) : n ? Tn("vertical", t) : Ql();
}
let Un = new AbortController();
function vn() {
  Un.abort(), Un = new AbortController();
  const e = {
    capture: !0,
    signal: Un.signal
  };
  An.size && (en ? (pe.length > 0 && Pe.forEach((n, t) => {
    const {
      body: c
    } = t;
    n > 0 && (c.addEventListener("contextmenu", kn, e), c.addEventListener("pointerleave", Mn, e), c.addEventListener("pointermove", Mn, e));
  }), window.addEventListener("pointerup", kn, e), window.addEventListener("pointercancel", kn, e)) : Pe.forEach((n, t) => {
    const {
      body: c
    } = t;
    n > 0 && (c.addEventListener("pointerdown", lg, e), c.addEventListener("pointermove", Mn, e));
  }));
}
function Vn(e, n) {
  An.forEach((t) => {
    const {
      setResizeHandlerState: c
    } = t, g = pe.includes(t);
    c(e, g, n);
  });
}
function gg() {
  const [e, n] = Ke(0);
  return Ae(() => n((t) => t + 1), []);
}
function J(e, n) {
  if (!e)
    throw console.error(n), Error(n);
}
function Te(e, n, t = at) {
  return e.toFixed(t) === n.toFixed(t) ? 0 : e > n ? 1 : -1;
}
function Le(e, n, t = at) {
  return Te(e, n, t) === 0;
}
function Ze(e, n, t) {
  return Te(e, n, t) === 0;
}
function rg(e, n, t) {
  if (e.length !== n.length)
    return !1;
  for (let c = 0; c < e.length; c++) {
    const g = e[c], r = n[c];
    if (!Ze(g, r, t))
      return !1;
  }
  return !0;
}
function $e({
  panelConstraints: e,
  panelIndex: n,
  size: t
}) {
  const c = e[n];
  J(c != null, `Panel constraints not found for index ${n}`);
  let {
    collapsedSize: g = 0,
    collapsible: r,
    maxSize: i = 100,
    minSize: I = 0
  } = c;
  if (Te(t, I) < 0)
    if (r) {
      const a = (g + I) / 2;
      Te(t, a) < 0 ? t = g : t = I;
    } else
      t = I;
  return t = Math.min(i, t), t = parseFloat(t.toFixed(at)), t;
}
function an({
  delta: e,
  initialLayout: n,
  panelConstraints: t,
  pivotIndices: c,
  prevLayout: g,
  trigger: r
}) {
  if (Ze(e, 0))
    return n;
  const i = [...n], [I, a] = c;
  J(I != null, "Invalid first pivot index"), J(a != null, "Invalid second pivot index");
  let s = 0;
  if (r === "keyboard") {
    {
      const C = e < 0 ? a : I, u = t[C];
      J(u, `Panel constraints not found for index ${C}`);
      const {
        collapsedSize: W = 0,
        collapsible: d,
        minSize: x = 0
      } = u;
      if (d) {
        const v = n[C];
        if (J(v != null, `Previous layout not found for panel index ${C}`), Ze(v, W)) {
          const m = x - v;
          Te(m, Math.abs(e)) > 0 && (e = e < 0 ? 0 - m : m);
        }
      }
    }
    {
      const C = e < 0 ? I : a, u = t[C];
      J(u, `No panel constraints found for index ${C}`);
      const {
        collapsedSize: W = 0,
        collapsible: d,
        minSize: x = 0
      } = u;
      if (d) {
        const v = n[C];
        if (J(v != null, `Previous layout not found for panel index ${C}`), Ze(v, x)) {
          const m = v - W;
          Te(m, Math.abs(e)) > 0 && (e = e < 0 ? 0 - m : m);
        }
      }
    }
  }
  {
    const C = e < 0 ? 1 : -1;
    let u = e < 0 ? a : I, W = 0;
    for (; ; ) {
      const x = n[u];
      J(x != null, `Previous layout not found for panel index ${u}`);
      const m = $e({
        panelConstraints: t,
        panelIndex: u,
        size: 100
      }) - x;
      if (W += m, u += C, u < 0 || u >= t.length)
        break;
    }
    const d = Math.min(Math.abs(e), Math.abs(W));
    e = e < 0 ? 0 - d : d;
  }
  {
    let u = e < 0 ? I : a;
    for (; u >= 0 && u < t.length; ) {
      const W = Math.abs(e) - Math.abs(s), d = n[u];
      J(d != null, `Previous layout not found for panel index ${u}`);
      const x = d - W, v = $e({
        panelConstraints: t,
        panelIndex: u,
        size: x
      });
      if (!Ze(d, v) && (s += d - v, i[u] = v, s.toPrecision(3).localeCompare(Math.abs(e).toPrecision(3), void 0, {
        numeric: !0
      }) >= 0))
        break;
      e < 0 ? u-- : u++;
    }
  }
  if (rg(g, i))
    return g;
  {
    const C = e < 0 ? a : I, u = n[C];
    J(u != null, `Previous layout not found for panel index ${C}`);
    const W = u + s, d = $e({
      panelConstraints: t,
      panelIndex: C,
      size: W
    });
    if (i[C] = d, !Ze(d, W)) {
      let x = W - d, m = e < 0 ? a : I;
      for (; m >= 0 && m < t.length; ) {
        const p = i[m];
        J(p != null, `Previous layout not found for panel index ${m}`);
        const h = p + x, L = $e({
          panelConstraints: t,
          panelIndex: m,
          size: h
        });
        if (Ze(p, L) || (x -= L - p, i[m] = L), Ze(x, 0))
          break;
        e > 0 ? m-- : m++;
      }
    }
  }
  const b = i.reduce((C, u) => u + C, 0);
  return Ze(b, 100) ? i : g;
}
function ig({
  layout: e,
  panelsArray: n,
  pivotIndices: t
}) {
  let c = 0, g = 100, r = 0, i = 0;
  const I = t[0];
  J(I != null, "No pivot index found"), n.forEach((C, u) => {
    const {
      constraints: W
    } = C, {
      maxSize: d = 100,
      minSize: x = 0
    } = W;
    u === I ? (c = x, g = d) : (r += x, i += d);
  });
  const a = Math.min(g, 100 - r), s = Math.max(c, 100 - i), b = e[I];
  return {
    valueMax: a,
    valueMin: s,
    valueNow: b
  };
}
function bn(e, n = document) {
  return Array.from(n.querySelectorAll(`[${$.resizeHandleId}][data-panel-group-id="${e}"]`));
}
function bc(e, n, t = document) {
  const g = bn(e, t).findIndex((r) => r.getAttribute($.resizeHandleId) === n);
  return g ?? null;
}
function dc(e, n, t) {
  const c = bc(e, n, t);
  return c != null ? [c, c + 1] : [-1, -1];
}
function mc(e, n = document) {
  var t;
  if (n instanceof HTMLElement && (n == null || (t = n.dataset) === null || t === void 0 ? void 0 : t.panelGroupId) == e)
    return n;
  const c = n.querySelector(`[data-panel-group][data-panel-group-id="${e}"]`);
  return c || null;
}
function Jn(e, n = document) {
  const t = n.querySelector(`[${$.resizeHandleId}="${e}"]`);
  return t || null;
}
function Ig(e, n, t, c = document) {
  var g, r, i, I;
  const a = Jn(n, c), s = bn(e, c), b = a ? s.indexOf(a) : -1, C = (g = (r = t[b]) === null || r === void 0 ? void 0 : r.id) !== null && g !== void 0 ? g : null, u = (i = (I = t[b + 1]) === null || I === void 0 ? void 0 : I.id) !== null && i !== void 0 ? i : null;
  return [C, u];
}
function ag({
  committedValuesRef: e,
  eagerValuesRef: n,
  groupId: t,
  layout: c,
  panelDataArray: g,
  panelGroupElement: r,
  setLayout: i
}) {
  be({
    didWarnAboutMissingResizeHandle: !1
  }), Oe(() => {
    if (!r)
      return;
    const I = bn(t, r);
    for (let a = 0; a < g.length - 1; a++) {
      const {
        valueMax: s,
        valueMin: b,
        valueNow: C
      } = ig({
        layout: c,
        panelsArray: g,
        pivotIndices: [a, a + 1]
      }), u = I[a];
      if (u != null) {
        const W = g[a];
        J(W, `No panel data found for index "${a}"`), u.setAttribute("aria-controls", W.id), u.setAttribute("aria-valuemax", "" + Math.round(s)), u.setAttribute("aria-valuemin", "" + Math.round(b)), u.setAttribute("aria-valuenow", C != null ? "" + Math.round(C) : "");
      }
    }
    return () => {
      I.forEach((a, s) => {
        a.removeAttribute("aria-controls"), a.removeAttribute("aria-valuemax"), a.removeAttribute("aria-valuemin"), a.removeAttribute("aria-valuenow");
      });
    };
  }, [t, c, g, r]), De(() => {
    if (!r)
      return;
    const I = n.current;
    J(I, "Eager values not found");
    const {
      panelDataArray: a
    } = I, s = mc(t, r);
    J(s != null, `No group found for id "${t}"`);
    const b = bn(t, r);
    J(b, `No resize handles found for group id "${t}"`);
    const C = b.map((u) => {
      const W = u.getAttribute($.resizeHandleId);
      J(W, "Resize handle element has no handle id attribute");
      const [d, x] = Ig(t, W, a, r);
      if (d == null || x == null)
        return () => {
        };
      const v = (m) => {
        if (!m.defaultPrevented)
          switch (m.key) {
            case "Enter": {
              m.preventDefault();
              const p = a.findIndex((h) => h.id === d);
              if (p >= 0) {
                const h = a[p];
                J(h, `No panel data found for index ${p}`);
                const L = c[p], {
                  collapsedSize: A = 0,
                  collapsible: z,
                  minSize: f = 0
                } = h.constraints;
                if (L != null && z) {
                  const ae = an({
                    delta: Ze(L, A) ? f - A : A - L,
                    initialLayout: c,
                    panelConstraints: a.map((Ce) => Ce.constraints),
                    pivotIndices: dc(t, W, r),
                    prevLayout: c,
                    trigger: "keyboard"
                  });
                  c !== ae && i(ae);
                }
              }
              break;
            }
          }
      };
      return u.addEventListener("keydown", v), () => {
        u.removeEventListener("keydown", v);
      };
    });
    return () => {
      C.forEach((u) => u());
    };
  }, [r, e, n, t, c, g, i]);
}
function St(e, n) {
  if (e.length !== n.length)
    return !1;
  for (let t = 0; t < e.length; t++)
    if (e[t] !== n[t])
      return !1;
  return !0;
}
function Zc(e, n) {
  const t = e === "horizontal", {
    x: c,
    y: g
  } = Rn(n);
  return t ? c : g;
}
function og(e, n, t, c, g) {
  const r = t === "horizontal", i = Jn(n, g);
  J(i, `No resize handle element found for id "${n}"`);
  const I = i.getAttribute($.groupId);
  J(I, "Resize handle element has no group id attribute");
  let {
    initialCursorPosition: a
  } = c;
  const s = Zc(t, e), b = mc(I, g);
  J(b, `No group element found for id "${I}"`);
  const C = b.getBoundingClientRect(), u = r ? C.width : C.height;
  return (s - a) / u * 100;
}
function Cg(e, n, t, c, g, r) {
  if (rc(e)) {
    const i = t === "horizontal";
    let I = 0;
    e.shiftKey ? I = 100 : g != null ? I = g : I = 10;
    let a = 0;
    switch (e.key) {
      case "ArrowDown":
        a = i ? 0 : I;
        break;
      case "ArrowLeft":
        a = i ? -I : 0;
        break;
      case "ArrowRight":
        a = i ? I : 0;
        break;
      case "ArrowUp":
        a = i ? 0 : -I;
        break;
      case "End":
        a = 100;
        break;
      case "Home":
        a = -100;
        break;
    }
    return a;
  } else
    return c == null ? 0 : og(e, n, t, c, r);
}
function ug({
  panelDataArray: e
}) {
  const n = Array(e.length), t = e.map((r) => r.constraints);
  let c = 0, g = 100;
  for (let r = 0; r < e.length; r++) {
    const i = t[r];
    J(i, `Panel constraints not found for index ${r}`);
    const {
      defaultSize: I
    } = i;
    I != null && (c++, n[r] = I, g -= I);
  }
  for (let r = 0; r < e.length; r++) {
    const i = t[r];
    J(i, `Panel constraints not found for index ${r}`);
    const {
      defaultSize: I
    } = i;
    if (I != null)
      continue;
    const a = e.length - c, s = g / a;
    c++, n[r] = s, g -= s;
  }
  return n;
}
function He(e, n, t) {
  n.forEach((c, g) => {
    const r = e[g];
    J(r, `Panel data not found for index ${g}`);
    const {
      callbacks: i,
      constraints: I,
      id: a
    } = r, {
      collapsedSize: s = 0,
      collapsible: b
    } = I, C = t[a];
    if (C == null || c !== C) {
      t[a] = c;
      const {
        onCollapse: u,
        onExpand: W,
        onResize: d
      } = i;
      d && d(c, C), b && (u || W) && (W && (C == null || Le(C, s)) && !Le(c, s) && W(), u && (C == null || !Le(C, s)) && Le(c, s) && u());
    }
  });
}
function Gn(e, n) {
  if (e.length !== n.length)
    return !1;
  for (let t = 0; t < e.length; t++)
    if (e[t] != n[t])
      return !1;
  return !0;
}
function sg({
  defaultSize: e,
  dragState: n,
  layout: t,
  panelData: c,
  panelIndex: g,
  precision: r = 3
}) {
  const i = t[g];
  let I;
  return i == null ? I = e != null ? e.toPrecision(r) : "1" : c.length === 1 ? I = "1" : I = i.toPrecision(r), {
    flexBasis: 0,
    flexGrow: I,
    flexShrink: 1,
    // Without this, Panel sizes may be unintentionally overridden by their content
    overflow: "hidden",
    // Disable pointer events inside of a panel during resize
    // This avoid edge cases like nested iframes
    pointerEvents: n !== null ? "none" : void 0
  };
}
function Ag(e, n = 10) {
  let t = null;
  return (...g) => {
    t !== null && clearTimeout(t), t = setTimeout(() => {
      e(...g);
    }, n);
  };
}
function Pt(e) {
  try {
    if (typeof localStorage < "u")
      e.getItem = (n) => localStorage.getItem(n), e.setItem = (n, t) => {
        localStorage.setItem(n, t);
      };
    else
      throw new Error("localStorage not supported in this environment");
  } catch (n) {
    console.error(n), e.getItem = () => null, e.setItem = () => {
    };
  }
}
function Gc(e) {
  return `react-resizable-panels:${e}`;
}
function fc(e) {
  return e.map((n) => {
    const {
      constraints: t,
      id: c,
      idIsFromProps: g,
      order: r
    } = n;
    return g ? c : r ? `${r}:${JSON.stringify(t)}` : JSON.stringify(t);
  }).sort((n, t) => n.localeCompare(t)).join(",");
}
function yc(e, n) {
  try {
    const t = Gc(e), c = n.getItem(t);
    if (c) {
      const g = JSON.parse(c);
      if (typeof g == "object" && g != null)
        return g;
    }
  } catch {
  }
  return null;
}
function bg(e, n, t) {
  var c, g;
  const r = (c = yc(e, t)) !== null && c !== void 0 ? c : {}, i = fc(n);
  return (g = r[i]) !== null && g !== void 0 ? g : null;
}
function dg(e, n, t, c, g) {
  var r;
  const i = Gc(e), I = fc(n), a = (r = yc(e, g)) !== null && r !== void 0 ? r : {};
  a[I] = {
    expandToSizes: Object.fromEntries(t.entries()),
    layout: c
  };
  try {
    g.setItem(i, JSON.stringify(a));
  } catch (s) {
    console.error(s);
  }
}
function Dt({
  layout: e,
  panelConstraints: n
}) {
  const t = [...e], c = t.reduce((r, i) => r + i, 0);
  if (t.length !== n.length)
    throw Error(`Invalid ${n.length} panel layout: ${t.map((r) => `${r}%`).join(", ")}`);
  if (!Ze(c, 100) && t.length > 0)
    for (let r = 0; r < n.length; r++) {
      const i = t[r];
      J(i != null, `No layout data found for index ${r}`);
      const I = 100 / c * i;
      t[r] = I;
    }
  let g = 0;
  for (let r = 0; r < n.length; r++) {
    const i = t[r];
    J(i != null, `No layout data found for index ${r}`);
    const I = $e({
      panelConstraints: n,
      panelIndex: r,
      size: i
    });
    i != I && (g += i - I, t[r] = I);
  }
  if (!Ze(g, 0))
    for (let r = 0; r < n.length; r++) {
      const i = t[r];
      J(i != null, `No layout data found for index ${r}`);
      const I = i + g, a = $e({
        panelConstraints: n,
        panelIndex: r,
        size: I
      });
      if (i !== a && (g -= a - i, t[r] = a, Ze(g, 0)))
        break;
    }
  return t;
}
const mg = 100, on = {
  getItem: (e) => (Pt(on), on.getItem(e)),
  setItem: (e, n) => {
    Pt(on), on.setItem(e, n);
  }
}, Ot = {};
function Wc({
  autoSaveId: e = null,
  children: n,
  className: t = "",
  direction: c,
  forwardedRef: g,
  id: r = null,
  onLayout: i = null,
  keyboardResizeBy: I = null,
  storage: a = on,
  style: s,
  tagName: b = "div",
  ...C
}) {
  const u = ot(r), W = be(null), [d, x] = Ke(null), [v, m] = Ke([]), p = gg(), h = be({}), L = be(/* @__PURE__ */ new Map()), A = be(0), z = be({
    autoSaveId: e,
    direction: c,
    dragState: d,
    id: u,
    keyboardResizeBy: I,
    onLayout: i,
    storage: a
  }), f = be({
    layout: v,
    panelDataArray: [],
    panelDataArrayChanged: !1
  });
  be({
    didLogIdAndOrderWarning: !1,
    didLogPanelConstraintsWarning: !1,
    prevPanelIds: []
  }), Mt(g, () => ({
    getId: () => z.current.id,
    getLayout: () => {
      const {
        layout: y
      } = f.current;
      return y;
    },
    setLayout: (y) => {
      const {
        onLayout: Y
      } = z.current, {
        layout: R,
        panelDataArray: V
      } = f.current, X = Dt({
        layout: y,
        panelConstraints: V.map((N) => N.constraints)
      });
      St(R, X) || (m(X), f.current.layout = X, Y && Y(X), He(V, X, h.current));
    }
  }), []), Oe(() => {
    z.current.autoSaveId = e, z.current.direction = c, z.current.dragState = d, z.current.id = u, z.current.onLayout = i, z.current.storage = a;
  }), ag({
    committedValuesRef: z,
    eagerValuesRef: f,
    groupId: u,
    layout: v,
    panelDataArray: f.current.panelDataArray,
    setLayout: m,
    panelGroupElement: W.current
  }), De(() => {
    const {
      panelDataArray: y
    } = f.current;
    if (e) {
      if (v.length === 0 || v.length !== y.length)
        return;
      let Y = Ot[e];
      Y == null && (Y = Ag(dg, mg), Ot[e] = Y);
      const R = [...y], V = new Map(L.current);
      Y(e, R, V, v, a);
    }
  }, [e, v, a]), De(() => {
  });
  const ae = Ae((y) => {
    const {
      onLayout: Y
    } = z.current, {
      layout: R,
      panelDataArray: V
    } = f.current;
    if (y.constraints.collapsible) {
      const X = V.map((ue) => ue.constraints), {
        collapsedSize: N = 0,
        panelSize: F,
        pivotIndices: k
      } = Se(V, y, R);
      if (J(F != null, `Panel size not found for panel "${y.id}"`), !Le(F, N)) {
        L.current.set(y.id, F);
        const G = _e(V, y) === V.length - 1 ? F - N : N - F, M = an({
          delta: G,
          initialLayout: R,
          panelConstraints: X,
          pivotIndices: k,
          prevLayout: R,
          trigger: "imperative-api"
        });
        Gn(R, M) || (m(M), f.current.layout = M, Y && Y(M), He(V, M, h.current));
      }
    }
  }, []), Ce = Ae((y, Y) => {
    const {
      onLayout: R
    } = z.current, {
      layout: V,
      panelDataArray: X
    } = f.current;
    if (y.constraints.collapsible) {
      const N = X.map((le) => le.constraints), {
        collapsedSize: F = 0,
        panelSize: k = 0,
        minSize: ue = 0,
        pivotIndices: G
      } = Se(X, y, V), M = Y ?? ue;
      if (Le(k, F)) {
        const le = L.current.get(y.id), me = le != null && le >= M ? le : M, Me = _e(X, y) === X.length - 1 ? k - me : me - k, re = an({
          delta: Me,
          initialLayout: V,
          panelConstraints: N,
          pivotIndices: G,
          prevLayout: V,
          trigger: "imperative-api"
        });
        Gn(V, re) || (m(re), f.current.layout = re, R && R(re), He(X, re, h.current));
      }
    }
  }, []), ge = Ae((y) => {
    const {
      layout: Y,
      panelDataArray: R
    } = f.current, {
      panelSize: V
    } = Se(R, y, Y);
    return J(V != null, `Panel size not found for panel "${y.id}"`), V;
  }, []), te = Ae((y, Y) => {
    const {
      panelDataArray: R
    } = f.current, V = _e(R, y);
    return sg({
      defaultSize: Y,
      dragState: d,
      layout: v,
      panelData: R,
      panelIndex: V
    });
  }, [d, v]), U = Ae((y) => {
    const {
      layout: Y,
      panelDataArray: R
    } = f.current, {
      collapsedSize: V = 0,
      collapsible: X,
      panelSize: N
    } = Se(R, y, Y);
    return J(N != null, `Panel size not found for panel "${y.id}"`), X === !0 && Le(N, V);
  }, []), ce = Ae((y) => {
    const {
      layout: Y,
      panelDataArray: R
    } = f.current, {
      collapsedSize: V = 0,
      collapsible: X,
      panelSize: N
    } = Se(R, y, Y);
    return J(N != null, `Panel size not found for panel "${y.id}"`), !X || Te(N, V) > 0;
  }, []), H = Ae((y) => {
    const {
      panelDataArray: Y
    } = f.current;
    Y.push(y), Y.sort((R, V) => {
      const X = R.order, N = V.order;
      return X == null && N == null ? 0 : X == null ? -1 : N == null ? 1 : X - N;
    }), f.current.panelDataArrayChanged = !0, p();
  }, [p]);
  Oe(() => {
    if (f.current.panelDataArrayChanged) {
      f.current.panelDataArrayChanged = !1;
      const {
        autoSaveId: y,
        onLayout: Y,
        storage: R
      } = z.current, {
        layout: V,
        panelDataArray: X
      } = f.current;
      let N = null;
      if (y) {
        const k = bg(y, X, R);
        k && (L.current = new Map(Object.entries(k.expandToSizes)), N = k.layout);
      }
      N == null && (N = ug({
        panelDataArray: X
      }));
      const F = Dt({
        layout: N,
        panelConstraints: X.map((k) => k.constraints)
      });
      St(V, F) || (m(F), f.current.layout = F, Y && Y(F), He(X, F, h.current));
    }
  }), Oe(() => {
    const y = f.current;
    return () => {
      y.layout = [];
    };
  }, []);
  const Q = Ae((y) => {
    let Y = !1;
    const R = W.current;
    return R && window.getComputedStyle(R, null).getPropertyValue("direction") === "rtl" && (Y = !0), function(X) {
      X.preventDefault();
      const N = W.current;
      if (!N)
        return () => null;
      const {
        direction: F,
        dragState: k,
        id: ue,
        keyboardResizeBy: G,
        onLayout: M
      } = z.current, {
        layout: le,
        panelDataArray: me
      } = f.current, {
        initialLayout: he
      } = k ?? {}, Me = dc(ue, y, N);
      let re = Cg(X, y, F, k, G, N);
      const we = F === "horizontal";
      we && Y && (re = -re);
      const wn = me.map((jn) => jn.constraints), je = an({
        delta: re,
        initialLayout: he ?? le,
        panelConstraints: wn,
        pivotIndices: Me,
        prevLayout: le,
        trigger: rc(X) ? "keyboard" : "mouse-or-touch"
      }), ke = !Gn(le, je);
      (ic(X) || Ic(X)) && A.current != re && (A.current = re, !ke && re !== 0 ? we ? En(y, re < 0 ? oc : Cc) : En(y, re < 0 ? uc : sc) : En(y, 0)), ke && (m(je), f.current.layout = je, M && M(je), He(me, je, h.current));
    };
  }, []), q = Ae((y, Y) => {
    const {
      onLayout: R
    } = z.current, {
      layout: V,
      panelDataArray: X
    } = f.current, N = X.map((le) => le.constraints), {
      panelSize: F,
      pivotIndices: k
    } = Se(X, y, V);
    J(F != null, `Panel size not found for panel "${y.id}"`);
    const G = _e(X, y) === X.length - 1 ? F - Y : Y - F, M = an({
      delta: G,
      initialLayout: V,
      panelConstraints: N,
      pivotIndices: k,
      prevLayout: V,
      trigger: "imperative-api"
    });
    Gn(V, M) || (m(M), f.current.layout = M, R && R(M), He(X, M, h.current));
  }, []), xe = Ae((y, Y) => {
    const {
      layout: R,
      panelDataArray: V
    } = f.current, {
      collapsedSize: X = 0,
      collapsible: N
    } = Y, {
      collapsedSize: F = 0,
      collapsible: k,
      maxSize: ue = 100,
      minSize: G = 0
    } = y.constraints, {
      panelSize: M
    } = Se(V, y, R);
    M != null && (N && k && Le(M, X) ? Le(X, F) || q(y, F) : M < G ? q(y, G) : M > ue && q(y, ue));
  }, [q]), ye = Ae((y, Y) => {
    const {
      direction: R
    } = z.current, {
      layout: V
    } = f.current;
    if (!W.current)
      return;
    const X = Jn(y, W.current);
    J(X, `Drag handle element not found for id "${y}"`);
    const N = Zc(R, Y);
    x({
      dragHandleId: y,
      dragHandleRect: X.getBoundingClientRect(),
      initialCursorPosition: N,
      initialLayout: V
    });
  }, []), ve = Ae(() => {
    x(null);
  }, []), Re = Ae((y) => {
    const {
      panelDataArray: Y
    } = f.current, R = _e(Y, y);
    R >= 0 && (Y.splice(R, 1), delete h.current[y.id], f.current.panelDataArrayChanged = !0, p());
  }, [p]), We = Ec(() => ({
    collapsePanel: ae,
    direction: c,
    dragState: d,
    expandPanel: Ce,
    getPanelSize: ge,
    getPanelStyle: te,
    groupId: u,
    isPanelCollapsed: U,
    isPanelExpanded: ce,
    reevaluatePanelConstraints: xe,
    registerPanel: H,
    registerResizeHandle: Q,
    resizePanel: q,
    startDragging: ye,
    stopDragging: ve,
    unregisterPanel: Re,
    panelGroupElement: W.current
  }), [ae, d, c, Ce, ge, te, u, U, ce, xe, H, Q, q, ye, ve, Re]), Ve = {
    display: "flex",
    flexDirection: c === "horizontal" ? "row" : "column",
    height: "100%",
    overflow: "hidden",
    width: "100%"
  };
  return nn(zn.Provider, {
    value: We
  }, nn(b, {
    ...C,
    children: n,
    className: t,
    id: r,
    ref: W,
    style: {
      ...Ve,
      ...s
    },
    // CSS selectors
    [$.group]: "",
    [$.groupDirection]: c,
    [$.groupId]: u
  }));
}
const nt = lt((e, n) => nn(Wc, {
  ...e,
  forwardedRef: n
}));
Wc.displayName = "PanelGroup";
nt.displayName = "forwardRef(PanelGroup)";
function _e(e, n) {
  return e.findIndex((t) => t === n || t.id === n.id);
}
function Se(e, n, t) {
  const c = _e(e, n), r = c === e.length - 1 ? [c - 1, c] : [c, c + 1], i = t[c];
  return {
    ...n.constraints,
    panelSize: i,
    pivotIndices: r
  };
}
function Zg({
  disabled: e,
  handleId: n,
  resizeHandler: t,
  panelGroupElement: c
}) {
  De(() => {
    if (e || t == null || c == null)
      return;
    const g = Jn(n, c);
    if (g == null)
      return;
    const r = (i) => {
      if (!i.defaultPrevented)
        switch (i.key) {
          case "ArrowDown":
          case "ArrowLeft":
          case "ArrowRight":
          case "ArrowUp":
          case "End":
          case "Home": {
            i.preventDefault(), t(i);
            break;
          }
          case "F6": {
            i.preventDefault();
            const I = g.getAttribute($.groupId);
            J(I, `No group element found for id "${I}"`);
            const a = bn(I, c), s = bc(I, n, c);
            J(s !== null, `No resize element found for id "${n}"`);
            const b = i.shiftKey ? s > 0 ? s - 1 : a.length - 1 : s + 1 < a.length ? s + 1 : 0;
            a[b].focus();
            break;
          }
        }
    };
    return g.addEventListener("keydown", r), () => {
      g.removeEventListener("keydown", r);
    };
  }, [c, e, n, t]);
}
function tt({
  children: e = null,
  className: n = "",
  disabled: t = !1,
  hitAreaMargins: c,
  id: g,
  onBlur: r,
  onClick: i,
  onDragging: I,
  onFocus: a,
  onPointerDown: s,
  onPointerUp: b,
  style: C = {},
  tabIndex: u = 0,
  tagName: W = "div",
  ...d
}) {
  var x, v;
  const m = be(null), p = be({
    onClick: i,
    onDragging: I,
    onPointerDown: s,
    onPointerUp: b
  });
  De(() => {
    p.current.onClick = i, p.current.onDragging = I, p.current.onPointerDown = s, p.current.onPointerUp = b;
  });
  const h = gt(zn);
  if (h === null)
    throw Error("PanelResizeHandle components must be rendered within a PanelGroup container");
  const {
    direction: L,
    groupId: A,
    registerResizeHandle: z,
    startDragging: f,
    stopDragging: ae,
    panelGroupElement: Ce
  } = h, ge = ot(g), [te, U] = Ke("inactive"), [ce, H] = Ke(!1), [Q, q] = Ke(null), xe = be({
    state: te
  });
  Oe(() => {
    xe.current.state = te;
  }), De(() => {
    if (t)
      q(null);
    else {
      const We = z(ge);
      q(() => We);
    }
  }, [t, ge, z]);
  const ye = (x = c == null ? void 0 : c.coarse) !== null && x !== void 0 ? x : 15, ve = (v = c == null ? void 0 : c.fine) !== null && v !== void 0 ? v : 5;
  return De(() => {
    if (t || Q == null)
      return;
    const We = m.current;
    J(We, "Element ref not attached");
    let Ve = !1;
    return cg(ge, We, L, {
      coarse: ye,
      fine: ve
    }, (Y, R, V) => {
      if (!R) {
        U("inactive");
        return;
      }
      switch (Y) {
        case "down": {
          U("drag"), Ve = !1, J(V, 'Expected event to be defined for "down" action'), f(ge, V);
          const {
            onDragging: X,
            onPointerDown: N
          } = p.current;
          X == null || X(!0), N == null || N();
          break;
        }
        case "move": {
          const {
            state: X
          } = xe.current;
          Ve = !0, X !== "drag" && U("hover"), J(V, 'Expected event to be defined for "move" action'), Q(V);
          break;
        }
        case "up": {
          U("hover"), ae();
          const {
            onClick: X,
            onDragging: N,
            onPointerUp: F
          } = p.current;
          N == null || N(!1), F == null || F(), Ve || X == null || X();
          break;
        }
      }
    });
  }, [ye, L, t, ve, z, ge, Q, f, ae]), Zg({
    disabled: t,
    handleId: ge,
    resizeHandler: Q,
    panelGroupElement: Ce
  }), nn(W, {
    ...d,
    children: e,
    className: n,
    id: g,
    onBlur: () => {
      H(!1), r == null || r();
    },
    onFocus: () => {
      H(!0), a == null || a();
    },
    ref: m,
    role: "separator",
    style: {
      ...{
        touchAction: "none",
        userSelect: "none"
      },
      ...C
    },
    tabIndex: u,
    // CSS selectors
    [$.groupDirection]: L,
    [$.groupId]: A,
    [$.resizeHandle]: "",
    [$.resizeHandleActive]: te === "drag" ? "pointer" : ce ? "keyboard" : void 0,
    [$.resizeHandleEnabled]: !t,
    [$.resizeHandleId]: ge,
    [$.resizeHandleState]: te
  });
}
tt.displayName = "PanelResizeHandle";
const Qe = ({
  contributionPoint: e,
  className: n,
  children: t
}) => {
  const c = Oc("plugins"), g = ct.useMemo(() => c.getAllViewContributions()[e] || [], [c, e]);
  return g.length === 0 ? /* @__PURE__ */ _("div", { className: n, children: t }) : (
    // 将 className 应用到包裹元素上
    /* @__PURE__ */ _("div", { className: n, children: g.map((r) => {
      const i = c.getComponent(r.pluginId, r.component);
      return i ? /* @__PURE__ */ _(i, {}, r.id) : (console.warn(`[core-layout] Component "${r.component}" from plugin "${r.pluginId}" not found for contribution point "${e}".`), null);
    }) })
  );
};
function Xe() {
  return "You have tried to stringify object returned from `css` function. It isn't supposed to be used directly (e.g. as value of the `className` prop), but rather handed to emotion so it can handle it (e.g. as value of `css` prop).";
}
const Gg = process.env.NODE_ENV === "production" ? {
  name: "64bz6a",
  styles: "display:flex;flex-direction:column;height:100vh;width:100vw;background-color:#1f2937;color:#d1d5db;font-family:sans-serif"
} : {
  name: "1ljes3n-workbenchStyle",
  styles: "display:flex;flex-direction:column;height:100vh;width:100vw;background-color:#1f2937;color:#d1d5db;font-family:sans-serif;label:workbenchStyle;/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIi9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFPMEIiLCJmaWxlIjoiL1VzZXJzL25pdXJ4L0hldm5vL3BsdWdpbnMvY29yZV9sYXlvdXQvY29tcG9uZW50cy9Xb3JrYmVuY2hMYXlvdXQudHN4Iiwic291cmNlc0NvbnRlbnQiOlsiLyoqIEBqc3hJbXBvcnRTb3VyY2UgQGVtb3Rpb24vcmVhY3QgKi9cbmltcG9ydCB7IGNzcyB9IGZyb20gJ0BlbW90aW9uL3JlYWN0JztcbmltcG9ydCBSZWFjdCBmcm9tICdyZWFjdCc7XG5pbXBvcnQgeyBQYW5lbCwgUGFuZWxHcm91cCwgUGFuZWxSZXNpemVIYW5kbGUgfSBmcm9tICdyZWFjdC1yZXNpemFibGUtcGFuZWxzJztcbmltcG9ydCBWaWV3UmVuZGVyZXIgZnJvbSAnLi9WaWV3UmVuZGVyZXInO1xuXG4vLyDkvb/nlKggRW1vdGlvbiDlrprkuYnmoLflvI9cbmNvbnN0IHdvcmtiZW5jaFN0eWxlID0gY3NzYFxuICBkaXNwbGF5OiBmbGV4O1xuICBmbGV4LWRpcmVjdGlvbjogY29sdW1uO1xuICBoZWlnaHQ6IDEwMHZoO1xuICB3aWR0aDogMTAwdnc7XG4gIGJhY2tncm91bmQtY29sb3I6ICMxZjI5Mzc7IC8vIGJnLWdyYXktODAwXG4gIGNvbG9yOiAjZDFkNWRiOyAvLyB0ZXh0LWdyYXktMjAwXG4gIGZvbnQtZmFtaWx5OiBzYW5zLXNlcmlmO1xuYDtcblxuY29uc3QgaGVhZGVyU3R5bGUgPSBjc3NgXG4gIGhlaWdodDogMnJlbTsgLyogaC04ICovXG4gIGJhY2tncm91bmQtY29sb3I6ICMxMTE4Mjc7IC8qIGJnLWdyYXktOTAwICovXG4gIGZsZXgtc2hyaW5rOiAwO1xuYDtcblxuY29uc3QgbWFpblN0eWxlID0gY3NzYFxuICBmbGV4LWdyb3c6IDE7XG4gIG1pbi1oZWlnaHQ6IDA7XG5gO1xuXG5jb25zdCBwYW5lbFN0eWxlID0gY3NzYFxuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMzc0MTUxOyAvKiBiZy1ncmF5LTcwMCAqL1xuYDtcblxuY29uc3QgcmVzaXplSGFuZGxlU3R5bGUgPSBjc3NgXG4gIGJhY2tncm91bmQtY29sb3I6ICMxMTE4Mjc7IC8qIGJnLWdyYXktOTAwICovXG4gIHRyYW5zaXRpb246IGJhY2tncm91bmQtY29sb3IgMC4ycztcbiAgJltkYXRhLXJlc2l6ZS1oYW5kbGUtc3RhdGU9XCJob3ZlclwiXSxcbiAgJltkYXRhLXJlc2l6ZS1oYW5kbGUtc3RhdGU9XCJkcmFnXCJdIHtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiAjM2I4MmY2OyAvKiBob3ZlcjpiZy1ibHVlLTUwMCAqL1xuICB9XG5gO1xuXG5jb25zdCBmb290ZXJTdHlsZSA9IGNzc2BcbiAgaGVpZ2h0OiAxLjVyZW07IC8qIGgtNiAqL1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMjU2M2ViOyAvKiBiZy1ibHVlLTYwMCAqL1xuICBmbGV4LXNocmluazogMDtcbiAgZGlzcGxheTogZmxleDtcbiAgYWxpZ24taXRlbXM6IGNlbnRlcjtcbiAganVzdGlmeS1jb250ZW50OiBzcGFjZS1iZXR3ZWVuO1xuICBwYWRkaW5nOiAwIDFyZW07IC8qIHB4LTQgKi9cbiAgZm9udC1zaXplOiAwLjc1cmVtOyAvKiB0ZXh0LXhzICovXG4gIGNvbG9yOiB3aGl0ZTtcbmA7XG5cbi8vIOe7hOS7tuWumuS5iVxuZXhwb3J0IGRlZmF1bHQgZnVuY3Rpb24gV29ya2JlbmNoTGF5b3V0KCkge1xuICByZXR1cm4gKFxuICAgIDxkaXYgY3NzPXt3b3JrYmVuY2hTdHlsZX0+XG4gICAgICA8aGVhZGVyIGNzcz17aGVhZGVyU3R5bGV9PlxuICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLnRpdGxlYmFyXCIgLz5cbiAgICAgIDwvaGVhZGVyPlxuXG4gICAgICA8bWFpbiBjc3M9e21haW5TdHlsZX0+XG4gICAgICAgIDxQYW5lbEdyb3VwIGRpcmVjdGlvbj1cImhvcml6b250YWxcIj5cbiAgICAgICAgICA8UGFuZWwgZGVmYXVsdFNpemU9ezIwfSBtaW5TaXplPXsxNX0+XG4gICAgICAgICAgICB7Lyog5L2g5Y+v5Lul55u05o6l5ZyoIFZpZXdSZW5kZXJlciDkuIrlhpkgY3NzIHByb3AgKi99XG4gICAgICAgICAgICA8Vmlld1JlbmRlcmVyIFxuICAgICAgICAgICAgICBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC5zaWRlYmFyXCIgXG4gICAgICAgICAgICAgIGNzcz17Y3NzYHBhZGRpbmc6IDAuNXJlbTsgZGlzcGxheTogZmxleDsgZmxleC1kaXJlY3Rpb246IGNvbHVtbjsgZ2FwOiAxcmVtOyBmbGV4LWdyb3c6IDE7YH0gXG4gICAgICAgICAgICAvPlxuICAgICAgICAgIDwvUGFuZWw+XG4gICAgICAgICAgPFBhbmVsUmVzaXplSGFuZGxlIGNzcz17cmVzaXplSGFuZGxlU3R5bGV9IHN0eWxlPXt7IHdpZHRoOiAnNHB4JyB9fSAvPlxuICAgICAgICAgIFxuICAgICAgICAgIDxQYW5lbD5cbiAgICAgICAgICAgIDxQYW5lbEdyb3VwIGRpcmVjdGlvbj1cInZlcnRpY2FsXCI+XG4gICAgICAgICAgICAgIDxQYW5lbCBkZWZhdWx0U2l6ZT17NzV9IG1pblNpemU9ezUwfSBjc3M9e3BhbmVsU3R5bGV9PlxuICAgICAgICAgICAgICAgIDxWaWV3UmVuZGVyZXIgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2gubWFpbi5jb250YWluZXJcIj5cbiAgICAgICAgICAgICAgICAgIDxkaXYgY3NzPXtjc3NgZGlzcGxheTogZmxleDsgYWxpZ24taXRlbXM6IGNlbnRlcjsganVzdGlmeS1jb250ZW50OiBjZW50ZXI7IGhlaWdodDogMTAwJTsgY29sb3I6ICM2YjcyODA7YH0+XG4gICAgICAgICAgICAgICAgICAgIDxwPk1haW4gQ29udGVudCBBcmVhPC9wPlxuICAgICAgICAgICAgICAgICAgPC9kaXY+XG4gICAgICAgICAgICAgICAgPC9WaWV3UmVuZGVyZXI+XG4gICAgICAgICAgICAgIDwvUGFuZWw+XG4gICAgICAgICAgICAgIDxQYW5lbFJlc2l6ZUhhbmRsZSBjc3M9e3Jlc2l6ZUhhbmRsZVN0eWxlfSBzdHlsZT17eyBoZWlnaHQ6ICc0cHgnIH19Lz5cbiAgICAgICAgICAgICAgPFBhbmVsIGRlZmF1bHRTaXplPXsyNX0gbWluU2l6ZT17MTB9PlxuICAgICAgICAgICAgICAgIDxWaWV3UmVuZGVyZXIgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2gucGFuZWwuY29udGFpbmVyXCI+XG4gICAgICAgICAgICAgICAgICA8ZGl2IGNzcz17Y3NzYHBhZGRpbmc6IDAuNXJlbTsgY29sb3I6ICM2YjcyODA7YH0+XG4gICAgICAgICAgICAgICAgICAgIDxwPlBhbmVsIEFyZWEgKGUuZy4sIENvbnNvbGUsIFRlcm1pbmFsKTwvcD5cbiAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgIDwvVmlld1JlbmRlcmVyPlxuICAgICAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgICAgPC9QYW5lbEdyb3VwPlxuICAgICAgICAgIDwvUGFuZWw+XG4gICAgICAgIDwvUGFuZWxHcm91cD5cbiAgICAgIDwvbWFpbj5cbiAgICAgIFxuICAgICAgPGZvb3RlciBjc3M9e2Zvb3RlclN0eWxlfT5cbiAgICAgICAgPGRpdiBjc3M9e2Nzc2BkaXNwbGF5OiBmbGV4OyBhbGlnbi1pdGVtczogY2VudGVyOyBnYXA6IDFyZW07YH0+XG4gICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLnN0YXR1c2Jhci5sZWZ0XCIgLz5cbiAgICAgICAgPC9kaXY+XG4gICAgICAgIDxkaXYgY3NzPXtjc3NgZGlzcGxheTogZmxleDsgYWxpZ24taXRlbXM6IGNlbnRlcjsgZ2FwOiAxcmVtO2B9PlxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC5zdGF0dXNiYXIucmlnaHRcIiAvPlxuICAgICAgICA8L2Rpdj5cbiAgICAgIDwvZm9vdGVyPlxuICAgIDwvZGl2PlxuICApO1xufVxuIl19 */",
  toString: Xe
}, fg = process.env.NODE_ENV === "production" ? {
  name: "1yrflp7",
  styles: "height:2rem;background-color:#111827;flex-shrink:0"
} : {
  name: "113swdx-headerStyle",
  styles: "height:2rem;background-color:#111827;flex-shrink:0;label:headerStyle;/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIi9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFpQnVCIiwiZmlsZSI6Ii9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCIsInNvdXJjZXNDb250ZW50IjpbIi8qKiBAanN4SW1wb3J0U291cmNlIEBlbW90aW9uL3JlYWN0ICovXG5pbXBvcnQgeyBjc3MgfSBmcm9tICdAZW1vdGlvbi9yZWFjdCc7XG5pbXBvcnQgUmVhY3QgZnJvbSAncmVhY3QnO1xuaW1wb3J0IHsgUGFuZWwsIFBhbmVsR3JvdXAsIFBhbmVsUmVzaXplSGFuZGxlIH0gZnJvbSAncmVhY3QtcmVzaXphYmxlLXBhbmVscyc7XG5pbXBvcnQgVmlld1JlbmRlcmVyIGZyb20gJy4vVmlld1JlbmRlcmVyJztcblxuLy8g5L2/55SoIEVtb3Rpb24g5a6a5LmJ5qC35byPXG5jb25zdCB3b3JrYmVuY2hTdHlsZSA9IGNzc2BcbiAgZGlzcGxheTogZmxleDtcbiAgZmxleC1kaXJlY3Rpb246IGNvbHVtbjtcbiAgaGVpZ2h0OiAxMDB2aDtcbiAgd2lkdGg6IDEwMHZ3O1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMWYyOTM3OyAvLyBiZy1ncmF5LTgwMFxuICBjb2xvcjogI2QxZDVkYjsgLy8gdGV4dC1ncmF5LTIwMFxuICBmb250LWZhbWlseTogc2Fucy1zZXJpZjtcbmA7XG5cbmNvbnN0IGhlYWRlclN0eWxlID0gY3NzYFxuICBoZWlnaHQ6IDJyZW07IC8qIGgtOCAqL1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICBmbGV4LXNocmluazogMDtcbmA7XG5cbmNvbnN0IG1haW5TdHlsZSA9IGNzc2BcbiAgZmxleC1ncm93OiAxO1xuICBtaW4taGVpZ2h0OiAwO1xuYDtcblxuY29uc3QgcGFuZWxTdHlsZSA9IGNzc2BcbiAgYmFja2dyb3VuZC1jb2xvcjogIzM3NDE1MTsgLyogYmctZ3JheS03MDAgKi9cbmA7XG5cbmNvbnN0IHJlc2l6ZUhhbmRsZVN0eWxlID0gY3NzYFxuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICB0cmFuc2l0aW9uOiBiYWNrZ3JvdW5kLWNvbG9yIDAuMnM7XG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiaG92ZXJcIl0sXG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiZHJhZ1wiXSB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogIzNiODJmNjsgLyogaG92ZXI6YmctYmx1ZS01MDAgKi9cbiAgfVxuYDtcblxuY29uc3QgZm9vdGVyU3R5bGUgPSBjc3NgXG4gIGhlaWdodDogMS41cmVtOyAvKiBoLTYgKi9cbiAgYmFja2dyb3VuZC1jb2xvcjogIzI1NjNlYjsgLyogYmctYmx1ZS02MDAgKi9cbiAgZmxleC1zaHJpbms6IDA7XG4gIGRpc3BsYXk6IGZsZXg7XG4gIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gIGp1c3RpZnktY29udGVudDogc3BhY2UtYmV0d2VlbjtcbiAgcGFkZGluZzogMCAxcmVtOyAvKiBweC00ICovXG4gIGZvbnQtc2l6ZTogMC43NXJlbTsgLyogdGV4dC14cyAqL1xuICBjb2xvcjogd2hpdGU7XG5gO1xuXG4vLyDnu4Tku7blrprkuYlcbmV4cG9ydCBkZWZhdWx0IGZ1bmN0aW9uIFdvcmtiZW5jaExheW91dCgpIHtcbiAgcmV0dXJuIChcbiAgICA8ZGl2IGNzcz17d29ya2JlbmNoU3R5bGV9PlxuICAgICAgPGhlYWRlciBjc3M9e2hlYWRlclN0eWxlfT5cbiAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC50aXRsZWJhclwiIC8+XG4gICAgICA8L2hlYWRlcj5cblxuICAgICAgPG1haW4gY3NzPXttYWluU3R5bGV9PlxuICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJob3Jpem9udGFsXCI+XG4gICAgICAgICAgPFBhbmVsIGRlZmF1bHRTaXplPXsyMH0gbWluU2l6ZT17MTV9PlxuICAgICAgICAgICAgey8qIOS9oOWPr+S7peebtOaOpeWcqCBWaWV3UmVuZGVyZXIg5LiK5YaZIGNzcyBwcm9wICovfVxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBcbiAgICAgICAgICAgICAgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc2lkZWJhclwiIFxuICAgICAgICAgICAgICBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGRpc3BsYXk6IGZsZXg7IGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47IGdhcDogMXJlbTsgZmxleC1ncm93OiAxO2B9IFxuICAgICAgICAgICAgLz5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgIDxQYW5lbFJlc2l6ZUhhbmRsZSBjc3M9e3Jlc2l6ZUhhbmRsZVN0eWxlfSBzdHlsZT17eyB3aWR0aDogJzRweCcgfX0gLz5cbiAgICAgICAgICBcbiAgICAgICAgICA8UGFuZWw+XG4gICAgICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJ2ZXJ0aWNhbFwiPlxuICAgICAgICAgICAgICA8UGFuZWwgZGVmYXVsdFNpemU9ezc1fSBtaW5TaXplPXs1MH0gY3NzPXtwYW5lbFN0eWxlfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLm1haW4uY29udGFpbmVyXCI+XG4gICAgICAgICAgICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGp1c3RpZnktY29udGVudDogY2VudGVyOyBoZWlnaHQ6IDEwMCU7IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5NYWluIENvbnRlbnQgQXJlYTwvcD5cbiAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgIDwvVmlld1JlbmRlcmVyPlxuICAgICAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgICAgICA8UGFuZWxSZXNpemVIYW5kbGUgY3NzPXtyZXNpemVIYW5kbGVTdHlsZX0gc3R5bGU9e3sgaGVpZ2h0OiAnNHB4JyB9fS8+XG4gICAgICAgICAgICAgIDxQYW5lbCBkZWZhdWx0U2l6ZT17MjV9IG1pblNpemU9ezEwfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLnBhbmVsLmNvbnRhaW5lclwiPlxuICAgICAgICAgICAgICAgICAgPGRpdiBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5QYW5lbCBBcmVhIChlLmcuLCBDb25zb2xlLCBUZXJtaW5hbCk8L3A+XG4gICAgICAgICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgICAgICAgICA8L1ZpZXdSZW5kZXJlcj5cbiAgICAgICAgICAgICAgPC9QYW5lbD5cbiAgICAgICAgICAgIDwvUGFuZWxHcm91cD5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICA8L1BhbmVsR3JvdXA+XG4gICAgICA8L21haW4+XG4gICAgICBcbiAgICAgIDxmb290ZXIgY3NzPXtmb290ZXJTdHlsZX0+XG4gICAgICAgIDxkaXYgY3NzPXtjc3NgZGlzcGxheTogZmxleDsgYWxpZ24taXRlbXM6IGNlbnRlcjsgZ2FwOiAxcmVtO2B9PlxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC5zdGF0dXNiYXIubGVmdFwiIC8+XG4gICAgICAgIDwvZGl2PlxuICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGdhcDogMXJlbTtgfT5cbiAgICAgICAgICAgIDxWaWV3UmVuZGVyZXIgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc3RhdHVzYmFyLnJpZ2h0XCIgLz5cbiAgICAgICAgPC9kaXY+XG4gICAgICA8L2Zvb3Rlcj5cbiAgICA8L2Rpdj5cbiAgKTtcbn1cbiJdfQ== */",
  toString: Xe
}, yg = process.env.NODE_ENV === "production" ? {
  name: "1p0lggj",
  styles: "flex-grow:1;min-height:0"
} : {
  name: "ywze99-mainStyle",
  styles: "flex-grow:1;min-height:0;label:mainStyle;/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIi9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUF1QnFCIiwiZmlsZSI6Ii9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCIsInNvdXJjZXNDb250ZW50IjpbIi8qKiBAanN4SW1wb3J0U291cmNlIEBlbW90aW9uL3JlYWN0ICovXG5pbXBvcnQgeyBjc3MgfSBmcm9tICdAZW1vdGlvbi9yZWFjdCc7XG5pbXBvcnQgUmVhY3QgZnJvbSAncmVhY3QnO1xuaW1wb3J0IHsgUGFuZWwsIFBhbmVsR3JvdXAsIFBhbmVsUmVzaXplSGFuZGxlIH0gZnJvbSAncmVhY3QtcmVzaXphYmxlLXBhbmVscyc7XG5pbXBvcnQgVmlld1JlbmRlcmVyIGZyb20gJy4vVmlld1JlbmRlcmVyJztcblxuLy8g5L2/55SoIEVtb3Rpb24g5a6a5LmJ5qC35byPXG5jb25zdCB3b3JrYmVuY2hTdHlsZSA9IGNzc2BcbiAgZGlzcGxheTogZmxleDtcbiAgZmxleC1kaXJlY3Rpb246IGNvbHVtbjtcbiAgaGVpZ2h0OiAxMDB2aDtcbiAgd2lkdGg6IDEwMHZ3O1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMWYyOTM3OyAvLyBiZy1ncmF5LTgwMFxuICBjb2xvcjogI2QxZDVkYjsgLy8gdGV4dC1ncmF5LTIwMFxuICBmb250LWZhbWlseTogc2Fucy1zZXJpZjtcbmA7XG5cbmNvbnN0IGhlYWRlclN0eWxlID0gY3NzYFxuICBoZWlnaHQ6IDJyZW07IC8qIGgtOCAqL1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICBmbGV4LXNocmluazogMDtcbmA7XG5cbmNvbnN0IG1haW5TdHlsZSA9IGNzc2BcbiAgZmxleC1ncm93OiAxO1xuICBtaW4taGVpZ2h0OiAwO1xuYDtcblxuY29uc3QgcGFuZWxTdHlsZSA9IGNzc2BcbiAgYmFja2dyb3VuZC1jb2xvcjogIzM3NDE1MTsgLyogYmctZ3JheS03MDAgKi9cbmA7XG5cbmNvbnN0IHJlc2l6ZUhhbmRsZVN0eWxlID0gY3NzYFxuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICB0cmFuc2l0aW9uOiBiYWNrZ3JvdW5kLWNvbG9yIDAuMnM7XG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiaG92ZXJcIl0sXG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiZHJhZ1wiXSB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogIzNiODJmNjsgLyogaG92ZXI6YmctYmx1ZS01MDAgKi9cbiAgfVxuYDtcblxuY29uc3QgZm9vdGVyU3R5bGUgPSBjc3NgXG4gIGhlaWdodDogMS41cmVtOyAvKiBoLTYgKi9cbiAgYmFja2dyb3VuZC1jb2xvcjogIzI1NjNlYjsgLyogYmctYmx1ZS02MDAgKi9cbiAgZmxleC1zaHJpbms6IDA7XG4gIGRpc3BsYXk6IGZsZXg7XG4gIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gIGp1c3RpZnktY29udGVudDogc3BhY2UtYmV0d2VlbjtcbiAgcGFkZGluZzogMCAxcmVtOyAvKiBweC00ICovXG4gIGZvbnQtc2l6ZTogMC43NXJlbTsgLyogdGV4dC14cyAqL1xuICBjb2xvcjogd2hpdGU7XG5gO1xuXG4vLyDnu4Tku7blrprkuYlcbmV4cG9ydCBkZWZhdWx0IGZ1bmN0aW9uIFdvcmtiZW5jaExheW91dCgpIHtcbiAgcmV0dXJuIChcbiAgICA8ZGl2IGNzcz17d29ya2JlbmNoU3R5bGV9PlxuICAgICAgPGhlYWRlciBjc3M9e2hlYWRlclN0eWxlfT5cbiAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC50aXRsZWJhclwiIC8+XG4gICAgICA8L2hlYWRlcj5cblxuICAgICAgPG1haW4gY3NzPXttYWluU3R5bGV9PlxuICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJob3Jpem9udGFsXCI+XG4gICAgICAgICAgPFBhbmVsIGRlZmF1bHRTaXplPXsyMH0gbWluU2l6ZT17MTV9PlxuICAgICAgICAgICAgey8qIOS9oOWPr+S7peebtOaOpeWcqCBWaWV3UmVuZGVyZXIg5LiK5YaZIGNzcyBwcm9wICovfVxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBcbiAgICAgICAgICAgICAgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc2lkZWJhclwiIFxuICAgICAgICAgICAgICBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGRpc3BsYXk6IGZsZXg7IGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47IGdhcDogMXJlbTsgZmxleC1ncm93OiAxO2B9IFxuICAgICAgICAgICAgLz5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgIDxQYW5lbFJlc2l6ZUhhbmRsZSBjc3M9e3Jlc2l6ZUhhbmRsZVN0eWxlfSBzdHlsZT17eyB3aWR0aDogJzRweCcgfX0gLz5cbiAgICAgICAgICBcbiAgICAgICAgICA8UGFuZWw+XG4gICAgICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJ2ZXJ0aWNhbFwiPlxuICAgICAgICAgICAgICA8UGFuZWwgZGVmYXVsdFNpemU9ezc1fSBtaW5TaXplPXs1MH0gY3NzPXtwYW5lbFN0eWxlfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLm1haW4uY29udGFpbmVyXCI+XG4gICAgICAgICAgICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGp1c3RpZnktY29udGVudDogY2VudGVyOyBoZWlnaHQ6IDEwMCU7IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5NYWluIENvbnRlbnQgQXJlYTwvcD5cbiAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgIDwvVmlld1JlbmRlcmVyPlxuICAgICAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgICAgICA8UGFuZWxSZXNpemVIYW5kbGUgY3NzPXtyZXNpemVIYW5kbGVTdHlsZX0gc3R5bGU9e3sgaGVpZ2h0OiAnNHB4JyB9fS8+XG4gICAgICAgICAgICAgIDxQYW5lbCBkZWZhdWx0U2l6ZT17MjV9IG1pblNpemU9ezEwfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLnBhbmVsLmNvbnRhaW5lclwiPlxuICAgICAgICAgICAgICAgICAgPGRpdiBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5QYW5lbCBBcmVhIChlLmcuLCBDb25zb2xlLCBUZXJtaW5hbCk8L3A+XG4gICAgICAgICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgICAgICAgICA8L1ZpZXdSZW5kZXJlcj5cbiAgICAgICAgICAgICAgPC9QYW5lbD5cbiAgICAgICAgICAgIDwvUGFuZWxHcm91cD5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICA8L1BhbmVsR3JvdXA+XG4gICAgICA8L21haW4+XG4gICAgICBcbiAgICAgIDxmb290ZXIgY3NzPXtmb290ZXJTdHlsZX0+XG4gICAgICAgIDxkaXYgY3NzPXtjc3NgZGlzcGxheTogZmxleDsgYWxpZ24taXRlbXM6IGNlbnRlcjsgZ2FwOiAxcmVtO2B9PlxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC5zdGF0dXNiYXIubGVmdFwiIC8+XG4gICAgICAgIDwvZGl2PlxuICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGdhcDogMXJlbTtgfT5cbiAgICAgICAgICAgIDxWaWV3UmVuZGVyZXIgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc3RhdHVzYmFyLnJpZ2h0XCIgLz5cbiAgICAgICAgPC9kaXY+XG4gICAgICA8L2Zvb3Rlcj5cbiAgICA8L2Rpdj5cbiAgKTtcbn1cbiJdfQ== */",
  toString: Xe
}, Wg = process.env.NODE_ENV === "production" ? {
  name: "1iwz9vn",
  styles: "background-color:#374151"
} : {
  name: "1y4u0cc-panelStyle",
  styles: "background-color:#374151;label:panelStyle;/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIi9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUE0QnNCIiwiZmlsZSI6Ii9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCIsInNvdXJjZXNDb250ZW50IjpbIi8qKiBAanN4SW1wb3J0U291cmNlIEBlbW90aW9uL3JlYWN0ICovXG5pbXBvcnQgeyBjc3MgfSBmcm9tICdAZW1vdGlvbi9yZWFjdCc7XG5pbXBvcnQgUmVhY3QgZnJvbSAncmVhY3QnO1xuaW1wb3J0IHsgUGFuZWwsIFBhbmVsR3JvdXAsIFBhbmVsUmVzaXplSGFuZGxlIH0gZnJvbSAncmVhY3QtcmVzaXphYmxlLXBhbmVscyc7XG5pbXBvcnQgVmlld1JlbmRlcmVyIGZyb20gJy4vVmlld1JlbmRlcmVyJztcblxuLy8g5L2/55SoIEVtb3Rpb24g5a6a5LmJ5qC35byPXG5jb25zdCB3b3JrYmVuY2hTdHlsZSA9IGNzc2BcbiAgZGlzcGxheTogZmxleDtcbiAgZmxleC1kaXJlY3Rpb246IGNvbHVtbjtcbiAgaGVpZ2h0OiAxMDB2aDtcbiAgd2lkdGg6IDEwMHZ3O1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMWYyOTM3OyAvLyBiZy1ncmF5LTgwMFxuICBjb2xvcjogI2QxZDVkYjsgLy8gdGV4dC1ncmF5LTIwMFxuICBmb250LWZhbWlseTogc2Fucy1zZXJpZjtcbmA7XG5cbmNvbnN0IGhlYWRlclN0eWxlID0gY3NzYFxuICBoZWlnaHQ6IDJyZW07IC8qIGgtOCAqL1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICBmbGV4LXNocmluazogMDtcbmA7XG5cbmNvbnN0IG1haW5TdHlsZSA9IGNzc2BcbiAgZmxleC1ncm93OiAxO1xuICBtaW4taGVpZ2h0OiAwO1xuYDtcblxuY29uc3QgcGFuZWxTdHlsZSA9IGNzc2BcbiAgYmFja2dyb3VuZC1jb2xvcjogIzM3NDE1MTsgLyogYmctZ3JheS03MDAgKi9cbmA7XG5cbmNvbnN0IHJlc2l6ZUhhbmRsZVN0eWxlID0gY3NzYFxuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICB0cmFuc2l0aW9uOiBiYWNrZ3JvdW5kLWNvbG9yIDAuMnM7XG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiaG92ZXJcIl0sXG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiZHJhZ1wiXSB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogIzNiODJmNjsgLyogaG92ZXI6YmctYmx1ZS01MDAgKi9cbiAgfVxuYDtcblxuY29uc3QgZm9vdGVyU3R5bGUgPSBjc3NgXG4gIGhlaWdodDogMS41cmVtOyAvKiBoLTYgKi9cbiAgYmFja2dyb3VuZC1jb2xvcjogIzI1NjNlYjsgLyogYmctYmx1ZS02MDAgKi9cbiAgZmxleC1zaHJpbms6IDA7XG4gIGRpc3BsYXk6IGZsZXg7XG4gIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gIGp1c3RpZnktY29udGVudDogc3BhY2UtYmV0d2VlbjtcbiAgcGFkZGluZzogMCAxcmVtOyAvKiBweC00ICovXG4gIGZvbnQtc2l6ZTogMC43NXJlbTsgLyogdGV4dC14cyAqL1xuICBjb2xvcjogd2hpdGU7XG5gO1xuXG4vLyDnu4Tku7blrprkuYlcbmV4cG9ydCBkZWZhdWx0IGZ1bmN0aW9uIFdvcmtiZW5jaExheW91dCgpIHtcbiAgcmV0dXJuIChcbiAgICA8ZGl2IGNzcz17d29ya2JlbmNoU3R5bGV9PlxuICAgICAgPGhlYWRlciBjc3M9e2hlYWRlclN0eWxlfT5cbiAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC50aXRsZWJhclwiIC8+XG4gICAgICA8L2hlYWRlcj5cblxuICAgICAgPG1haW4gY3NzPXttYWluU3R5bGV9PlxuICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJob3Jpem9udGFsXCI+XG4gICAgICAgICAgPFBhbmVsIGRlZmF1bHRTaXplPXsyMH0gbWluU2l6ZT17MTV9PlxuICAgICAgICAgICAgey8qIOS9oOWPr+S7peebtOaOpeWcqCBWaWV3UmVuZGVyZXIg5LiK5YaZIGNzcyBwcm9wICovfVxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBcbiAgICAgICAgICAgICAgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc2lkZWJhclwiIFxuICAgICAgICAgICAgICBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGRpc3BsYXk6IGZsZXg7IGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47IGdhcDogMXJlbTsgZmxleC1ncm93OiAxO2B9IFxuICAgICAgICAgICAgLz5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgIDxQYW5lbFJlc2l6ZUhhbmRsZSBjc3M9e3Jlc2l6ZUhhbmRsZVN0eWxlfSBzdHlsZT17eyB3aWR0aDogJzRweCcgfX0gLz5cbiAgICAgICAgICBcbiAgICAgICAgICA8UGFuZWw+XG4gICAgICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJ2ZXJ0aWNhbFwiPlxuICAgICAgICAgICAgICA8UGFuZWwgZGVmYXVsdFNpemU9ezc1fSBtaW5TaXplPXs1MH0gY3NzPXtwYW5lbFN0eWxlfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLm1haW4uY29udGFpbmVyXCI+XG4gICAgICAgICAgICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGp1c3RpZnktY29udGVudDogY2VudGVyOyBoZWlnaHQ6IDEwMCU7IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5NYWluIENvbnRlbnQgQXJlYTwvcD5cbiAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgIDwvVmlld1JlbmRlcmVyPlxuICAgICAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgICAgICA8UGFuZWxSZXNpemVIYW5kbGUgY3NzPXtyZXNpemVIYW5kbGVTdHlsZX0gc3R5bGU9e3sgaGVpZ2h0OiAnNHB4JyB9fS8+XG4gICAgICAgICAgICAgIDxQYW5lbCBkZWZhdWx0U2l6ZT17MjV9IG1pblNpemU9ezEwfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLnBhbmVsLmNvbnRhaW5lclwiPlxuICAgICAgICAgICAgICAgICAgPGRpdiBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5QYW5lbCBBcmVhIChlLmcuLCBDb25zb2xlLCBUZXJtaW5hbCk8L3A+XG4gICAgICAgICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgICAgICAgICA8L1ZpZXdSZW5kZXJlcj5cbiAgICAgICAgICAgICAgPC9QYW5lbD5cbiAgICAgICAgICAgIDwvUGFuZWxHcm91cD5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICA8L1BhbmVsR3JvdXA+XG4gICAgICA8L21haW4+XG4gICAgICBcbiAgICAgIDxmb290ZXIgY3NzPXtmb290ZXJTdHlsZX0+XG4gICAgICAgIDxkaXYgY3NzPXtjc3NgZGlzcGxheTogZmxleDsgYWxpZ24taXRlbXM6IGNlbnRlcjsgZ2FwOiAxcmVtO2B9PlxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC5zdGF0dXNiYXIubGVmdFwiIC8+XG4gICAgICAgIDwvZGl2PlxuICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGdhcDogMXJlbTtgfT5cbiAgICAgICAgICAgIDxWaWV3UmVuZGVyZXIgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc3RhdHVzYmFyLnJpZ2h0XCIgLz5cbiAgICAgICAgPC9kaXY+XG4gICAgICA8L2Zvb3Rlcj5cbiAgICA8L2Rpdj5cbiAgKTtcbn1cbiJdfQ== */",
  toString: Xe
}, Tt = process.env.NODE_ENV === "production" ? {
  name: "qv6zjx",
  styles: 'background-color:#111827;transition:background-color 0.2s;&[data-resize-handle-state="hover"],&[data-resize-handle-state="drag"]{background-color:#3b82f6;}'
} : {
  name: "fr68kd-resizeHandleStyle",
  styles: 'background-color:#111827;transition:background-color 0.2s;&[data-resize-handle-state="hover"],&[data-resize-handle-state="drag"]{background-color:#3b82f6;};label:resizeHandleStyle;/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIi9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFnQzZCIiwiZmlsZSI6Ii9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCIsInNvdXJjZXNDb250ZW50IjpbIi8qKiBAanN4SW1wb3J0U291cmNlIEBlbW90aW9uL3JlYWN0ICovXG5pbXBvcnQgeyBjc3MgfSBmcm9tICdAZW1vdGlvbi9yZWFjdCc7XG5pbXBvcnQgUmVhY3QgZnJvbSAncmVhY3QnO1xuaW1wb3J0IHsgUGFuZWwsIFBhbmVsR3JvdXAsIFBhbmVsUmVzaXplSGFuZGxlIH0gZnJvbSAncmVhY3QtcmVzaXphYmxlLXBhbmVscyc7XG5pbXBvcnQgVmlld1JlbmRlcmVyIGZyb20gJy4vVmlld1JlbmRlcmVyJztcblxuLy8g5L2/55SoIEVtb3Rpb24g5a6a5LmJ5qC35byPXG5jb25zdCB3b3JrYmVuY2hTdHlsZSA9IGNzc2BcbiAgZGlzcGxheTogZmxleDtcbiAgZmxleC1kaXJlY3Rpb246IGNvbHVtbjtcbiAgaGVpZ2h0OiAxMDB2aDtcbiAgd2lkdGg6IDEwMHZ3O1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMWYyOTM3OyAvLyBiZy1ncmF5LTgwMFxuICBjb2xvcjogI2QxZDVkYjsgLy8gdGV4dC1ncmF5LTIwMFxuICBmb250LWZhbWlseTogc2Fucy1zZXJpZjtcbmA7XG5cbmNvbnN0IGhlYWRlclN0eWxlID0gY3NzYFxuICBoZWlnaHQ6IDJyZW07IC8qIGgtOCAqL1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICBmbGV4LXNocmluazogMDtcbmA7XG5cbmNvbnN0IG1haW5TdHlsZSA9IGNzc2BcbiAgZmxleC1ncm93OiAxO1xuICBtaW4taGVpZ2h0OiAwO1xuYDtcblxuY29uc3QgcGFuZWxTdHlsZSA9IGNzc2BcbiAgYmFja2dyb3VuZC1jb2xvcjogIzM3NDE1MTsgLyogYmctZ3JheS03MDAgKi9cbmA7XG5cbmNvbnN0IHJlc2l6ZUhhbmRsZVN0eWxlID0gY3NzYFxuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICB0cmFuc2l0aW9uOiBiYWNrZ3JvdW5kLWNvbG9yIDAuMnM7XG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiaG92ZXJcIl0sXG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiZHJhZ1wiXSB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogIzNiODJmNjsgLyogaG92ZXI6YmctYmx1ZS01MDAgKi9cbiAgfVxuYDtcblxuY29uc3QgZm9vdGVyU3R5bGUgPSBjc3NgXG4gIGhlaWdodDogMS41cmVtOyAvKiBoLTYgKi9cbiAgYmFja2dyb3VuZC1jb2xvcjogIzI1NjNlYjsgLyogYmctYmx1ZS02MDAgKi9cbiAgZmxleC1zaHJpbms6IDA7XG4gIGRpc3BsYXk6IGZsZXg7XG4gIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gIGp1c3RpZnktY29udGVudDogc3BhY2UtYmV0d2VlbjtcbiAgcGFkZGluZzogMCAxcmVtOyAvKiBweC00ICovXG4gIGZvbnQtc2l6ZTogMC43NXJlbTsgLyogdGV4dC14cyAqL1xuICBjb2xvcjogd2hpdGU7XG5gO1xuXG4vLyDnu4Tku7blrprkuYlcbmV4cG9ydCBkZWZhdWx0IGZ1bmN0aW9uIFdvcmtiZW5jaExheW91dCgpIHtcbiAgcmV0dXJuIChcbiAgICA8ZGl2IGNzcz17d29ya2JlbmNoU3R5bGV9PlxuICAgICAgPGhlYWRlciBjc3M9e2hlYWRlclN0eWxlfT5cbiAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC50aXRsZWJhclwiIC8+XG4gICAgICA8L2hlYWRlcj5cblxuICAgICAgPG1haW4gY3NzPXttYWluU3R5bGV9PlxuICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJob3Jpem9udGFsXCI+XG4gICAgICAgICAgPFBhbmVsIGRlZmF1bHRTaXplPXsyMH0gbWluU2l6ZT17MTV9PlxuICAgICAgICAgICAgey8qIOS9oOWPr+S7peebtOaOpeWcqCBWaWV3UmVuZGVyZXIg5LiK5YaZIGNzcyBwcm9wICovfVxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBcbiAgICAgICAgICAgICAgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc2lkZWJhclwiIFxuICAgICAgICAgICAgICBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGRpc3BsYXk6IGZsZXg7IGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47IGdhcDogMXJlbTsgZmxleC1ncm93OiAxO2B9IFxuICAgICAgICAgICAgLz5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgIDxQYW5lbFJlc2l6ZUhhbmRsZSBjc3M9e3Jlc2l6ZUhhbmRsZVN0eWxlfSBzdHlsZT17eyB3aWR0aDogJzRweCcgfX0gLz5cbiAgICAgICAgICBcbiAgICAgICAgICA8UGFuZWw+XG4gICAgICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJ2ZXJ0aWNhbFwiPlxuICAgICAgICAgICAgICA8UGFuZWwgZGVmYXVsdFNpemU9ezc1fSBtaW5TaXplPXs1MH0gY3NzPXtwYW5lbFN0eWxlfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLm1haW4uY29udGFpbmVyXCI+XG4gICAgICAgICAgICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGp1c3RpZnktY29udGVudDogY2VudGVyOyBoZWlnaHQ6IDEwMCU7IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5NYWluIENvbnRlbnQgQXJlYTwvcD5cbiAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgIDwvVmlld1JlbmRlcmVyPlxuICAgICAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgICAgICA8UGFuZWxSZXNpemVIYW5kbGUgY3NzPXtyZXNpemVIYW5kbGVTdHlsZX0gc3R5bGU9e3sgaGVpZ2h0OiAnNHB4JyB9fS8+XG4gICAgICAgICAgICAgIDxQYW5lbCBkZWZhdWx0U2l6ZT17MjV9IG1pblNpemU9ezEwfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLnBhbmVsLmNvbnRhaW5lclwiPlxuICAgICAgICAgICAgICAgICAgPGRpdiBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5QYW5lbCBBcmVhIChlLmcuLCBDb25zb2xlLCBUZXJtaW5hbCk8L3A+XG4gICAgICAgICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgICAgICAgICA8L1ZpZXdSZW5kZXJlcj5cbiAgICAgICAgICAgICAgPC9QYW5lbD5cbiAgICAgICAgICAgIDwvUGFuZWxHcm91cD5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICA8L1BhbmVsR3JvdXA+XG4gICAgICA8L21haW4+XG4gICAgICBcbiAgICAgIDxmb290ZXIgY3NzPXtmb290ZXJTdHlsZX0+XG4gICAgICAgIDxkaXYgY3NzPXtjc3NgZGlzcGxheTogZmxleDsgYWxpZ24taXRlbXM6IGNlbnRlcjsgZ2FwOiAxcmVtO2B9PlxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC5zdGF0dXNiYXIubGVmdFwiIC8+XG4gICAgICAgIDwvZGl2PlxuICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGdhcDogMXJlbTtgfT5cbiAgICAgICAgICAgIDxWaWV3UmVuZGVyZXIgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc3RhdHVzYmFyLnJpZ2h0XCIgLz5cbiAgICAgICAgPC9kaXY+XG4gICAgICA8L2Zvb3Rlcj5cbiAgICA8L2Rpdj5cbiAgKTtcbn1cbiJdfQ== */',
  toString: Xe
}, pg = process.env.NODE_ENV === "production" ? {
  name: "8xfnnr",
  styles: "height:1.5rem;background-color:#2563eb;flex-shrink:0;display:flex;align-items:center;justify-content:space-between;padding:0 1rem;font-size:0.75rem;color:white"
} : {
  name: "9iwyha-footerStyle",
  styles: "height:1.5rem;background-color:#2563eb;flex-shrink:0;display:flex;align-items:center;justify-content:space-between;padding:0 1rem;font-size:0.75rem;color:white;label:footerStyle;/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIi9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUF5Q3VCIiwiZmlsZSI6Ii9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCIsInNvdXJjZXNDb250ZW50IjpbIi8qKiBAanN4SW1wb3J0U291cmNlIEBlbW90aW9uL3JlYWN0ICovXG5pbXBvcnQgeyBjc3MgfSBmcm9tICdAZW1vdGlvbi9yZWFjdCc7XG5pbXBvcnQgUmVhY3QgZnJvbSAncmVhY3QnO1xuaW1wb3J0IHsgUGFuZWwsIFBhbmVsR3JvdXAsIFBhbmVsUmVzaXplSGFuZGxlIH0gZnJvbSAncmVhY3QtcmVzaXphYmxlLXBhbmVscyc7XG5pbXBvcnQgVmlld1JlbmRlcmVyIGZyb20gJy4vVmlld1JlbmRlcmVyJztcblxuLy8g5L2/55SoIEVtb3Rpb24g5a6a5LmJ5qC35byPXG5jb25zdCB3b3JrYmVuY2hTdHlsZSA9IGNzc2BcbiAgZGlzcGxheTogZmxleDtcbiAgZmxleC1kaXJlY3Rpb246IGNvbHVtbjtcbiAgaGVpZ2h0OiAxMDB2aDtcbiAgd2lkdGg6IDEwMHZ3O1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMWYyOTM3OyAvLyBiZy1ncmF5LTgwMFxuICBjb2xvcjogI2QxZDVkYjsgLy8gdGV4dC1ncmF5LTIwMFxuICBmb250LWZhbWlseTogc2Fucy1zZXJpZjtcbmA7XG5cbmNvbnN0IGhlYWRlclN0eWxlID0gY3NzYFxuICBoZWlnaHQ6IDJyZW07IC8qIGgtOCAqL1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICBmbGV4LXNocmluazogMDtcbmA7XG5cbmNvbnN0IG1haW5TdHlsZSA9IGNzc2BcbiAgZmxleC1ncm93OiAxO1xuICBtaW4taGVpZ2h0OiAwO1xuYDtcblxuY29uc3QgcGFuZWxTdHlsZSA9IGNzc2BcbiAgYmFja2dyb3VuZC1jb2xvcjogIzM3NDE1MTsgLyogYmctZ3JheS03MDAgKi9cbmA7XG5cbmNvbnN0IHJlc2l6ZUhhbmRsZVN0eWxlID0gY3NzYFxuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICB0cmFuc2l0aW9uOiBiYWNrZ3JvdW5kLWNvbG9yIDAuMnM7XG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiaG92ZXJcIl0sXG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiZHJhZ1wiXSB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogIzNiODJmNjsgLyogaG92ZXI6YmctYmx1ZS01MDAgKi9cbiAgfVxuYDtcblxuY29uc3QgZm9vdGVyU3R5bGUgPSBjc3NgXG4gIGhlaWdodDogMS41cmVtOyAvKiBoLTYgKi9cbiAgYmFja2dyb3VuZC1jb2xvcjogIzI1NjNlYjsgLyogYmctYmx1ZS02MDAgKi9cbiAgZmxleC1zaHJpbms6IDA7XG4gIGRpc3BsYXk6IGZsZXg7XG4gIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gIGp1c3RpZnktY29udGVudDogc3BhY2UtYmV0d2VlbjtcbiAgcGFkZGluZzogMCAxcmVtOyAvKiBweC00ICovXG4gIGZvbnQtc2l6ZTogMC43NXJlbTsgLyogdGV4dC14cyAqL1xuICBjb2xvcjogd2hpdGU7XG5gO1xuXG4vLyDnu4Tku7blrprkuYlcbmV4cG9ydCBkZWZhdWx0IGZ1bmN0aW9uIFdvcmtiZW5jaExheW91dCgpIHtcbiAgcmV0dXJuIChcbiAgICA8ZGl2IGNzcz17d29ya2JlbmNoU3R5bGV9PlxuICAgICAgPGhlYWRlciBjc3M9e2hlYWRlclN0eWxlfT5cbiAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC50aXRsZWJhclwiIC8+XG4gICAgICA8L2hlYWRlcj5cblxuICAgICAgPG1haW4gY3NzPXttYWluU3R5bGV9PlxuICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJob3Jpem9udGFsXCI+XG4gICAgICAgICAgPFBhbmVsIGRlZmF1bHRTaXplPXsyMH0gbWluU2l6ZT17MTV9PlxuICAgICAgICAgICAgey8qIOS9oOWPr+S7peebtOaOpeWcqCBWaWV3UmVuZGVyZXIg5LiK5YaZIGNzcyBwcm9wICovfVxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBcbiAgICAgICAgICAgICAgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc2lkZWJhclwiIFxuICAgICAgICAgICAgICBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGRpc3BsYXk6IGZsZXg7IGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47IGdhcDogMXJlbTsgZmxleC1ncm93OiAxO2B9IFxuICAgICAgICAgICAgLz5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgIDxQYW5lbFJlc2l6ZUhhbmRsZSBjc3M9e3Jlc2l6ZUhhbmRsZVN0eWxlfSBzdHlsZT17eyB3aWR0aDogJzRweCcgfX0gLz5cbiAgICAgICAgICBcbiAgICAgICAgICA8UGFuZWw+XG4gICAgICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJ2ZXJ0aWNhbFwiPlxuICAgICAgICAgICAgICA8UGFuZWwgZGVmYXVsdFNpemU9ezc1fSBtaW5TaXplPXs1MH0gY3NzPXtwYW5lbFN0eWxlfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLm1haW4uY29udGFpbmVyXCI+XG4gICAgICAgICAgICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGp1c3RpZnktY29udGVudDogY2VudGVyOyBoZWlnaHQ6IDEwMCU7IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5NYWluIENvbnRlbnQgQXJlYTwvcD5cbiAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgIDwvVmlld1JlbmRlcmVyPlxuICAgICAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgICAgICA8UGFuZWxSZXNpemVIYW5kbGUgY3NzPXtyZXNpemVIYW5kbGVTdHlsZX0gc3R5bGU9e3sgaGVpZ2h0OiAnNHB4JyB9fS8+XG4gICAgICAgICAgICAgIDxQYW5lbCBkZWZhdWx0U2l6ZT17MjV9IG1pblNpemU9ezEwfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLnBhbmVsLmNvbnRhaW5lclwiPlxuICAgICAgICAgICAgICAgICAgPGRpdiBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5QYW5lbCBBcmVhIChlLmcuLCBDb25zb2xlLCBUZXJtaW5hbCk8L3A+XG4gICAgICAgICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgICAgICAgICA8L1ZpZXdSZW5kZXJlcj5cbiAgICAgICAgICAgICAgPC9QYW5lbD5cbiAgICAgICAgICAgIDwvUGFuZWxHcm91cD5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICA8L1BhbmVsR3JvdXA+XG4gICAgICA8L21haW4+XG4gICAgICBcbiAgICAgIDxmb290ZXIgY3NzPXtmb290ZXJTdHlsZX0+XG4gICAgICAgIDxkaXYgY3NzPXtjc3NgZGlzcGxheTogZmxleDsgYWxpZ24taXRlbXM6IGNlbnRlcjsgZ2FwOiAxcmVtO2B9PlxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC5zdGF0dXNiYXIubGVmdFwiIC8+XG4gICAgICAgIDwvZGl2PlxuICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGdhcDogMXJlbTtgfT5cbiAgICAgICAgICAgIDxWaWV3UmVuZGVyZXIgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc3RhdHVzYmFyLnJpZ2h0XCIgLz5cbiAgICAgICAgPC9kaXY+XG4gICAgICA8L2Zvb3Rlcj5cbiAgICA8L2Rpdj5cbiAgKTtcbn1cbiJdfQ== */",
  toString: Xe
};
var Xg = process.env.NODE_ENV === "production" ? {
  name: "r2g86h",
  styles: "display:flex;align-items:center;gap:1rem"
} : {
  name: "zy6fgs-WorkbenchLayout",
  styles: "display:flex;align-items:center;gap:1rem;label:WorkbenchLayout;/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIi9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFrR3FCIiwiZmlsZSI6Ii9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCIsInNvdXJjZXNDb250ZW50IjpbIi8qKiBAanN4SW1wb3J0U291cmNlIEBlbW90aW9uL3JlYWN0ICovXG5pbXBvcnQgeyBjc3MgfSBmcm9tICdAZW1vdGlvbi9yZWFjdCc7XG5pbXBvcnQgUmVhY3QgZnJvbSAncmVhY3QnO1xuaW1wb3J0IHsgUGFuZWwsIFBhbmVsR3JvdXAsIFBhbmVsUmVzaXplSGFuZGxlIH0gZnJvbSAncmVhY3QtcmVzaXphYmxlLXBhbmVscyc7XG5pbXBvcnQgVmlld1JlbmRlcmVyIGZyb20gJy4vVmlld1JlbmRlcmVyJztcblxuLy8g5L2/55SoIEVtb3Rpb24g5a6a5LmJ5qC35byPXG5jb25zdCB3b3JrYmVuY2hTdHlsZSA9IGNzc2BcbiAgZGlzcGxheTogZmxleDtcbiAgZmxleC1kaXJlY3Rpb246IGNvbHVtbjtcbiAgaGVpZ2h0OiAxMDB2aDtcbiAgd2lkdGg6IDEwMHZ3O1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMWYyOTM3OyAvLyBiZy1ncmF5LTgwMFxuICBjb2xvcjogI2QxZDVkYjsgLy8gdGV4dC1ncmF5LTIwMFxuICBmb250LWZhbWlseTogc2Fucy1zZXJpZjtcbmA7XG5cbmNvbnN0IGhlYWRlclN0eWxlID0gY3NzYFxuICBoZWlnaHQ6IDJyZW07IC8qIGgtOCAqL1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICBmbGV4LXNocmluazogMDtcbmA7XG5cbmNvbnN0IG1haW5TdHlsZSA9IGNzc2BcbiAgZmxleC1ncm93OiAxO1xuICBtaW4taGVpZ2h0OiAwO1xuYDtcblxuY29uc3QgcGFuZWxTdHlsZSA9IGNzc2BcbiAgYmFja2dyb3VuZC1jb2xvcjogIzM3NDE1MTsgLyogYmctZ3JheS03MDAgKi9cbmA7XG5cbmNvbnN0IHJlc2l6ZUhhbmRsZVN0eWxlID0gY3NzYFxuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICB0cmFuc2l0aW9uOiBiYWNrZ3JvdW5kLWNvbG9yIDAuMnM7XG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiaG92ZXJcIl0sXG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiZHJhZ1wiXSB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogIzNiODJmNjsgLyogaG92ZXI6YmctYmx1ZS01MDAgKi9cbiAgfVxuYDtcblxuY29uc3QgZm9vdGVyU3R5bGUgPSBjc3NgXG4gIGhlaWdodDogMS41cmVtOyAvKiBoLTYgKi9cbiAgYmFja2dyb3VuZC1jb2xvcjogIzI1NjNlYjsgLyogYmctYmx1ZS02MDAgKi9cbiAgZmxleC1zaHJpbms6IDA7XG4gIGRpc3BsYXk6IGZsZXg7XG4gIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gIGp1c3RpZnktY29udGVudDogc3BhY2UtYmV0d2VlbjtcbiAgcGFkZGluZzogMCAxcmVtOyAvKiBweC00ICovXG4gIGZvbnQtc2l6ZTogMC43NXJlbTsgLyogdGV4dC14cyAqL1xuICBjb2xvcjogd2hpdGU7XG5gO1xuXG4vLyDnu4Tku7blrprkuYlcbmV4cG9ydCBkZWZhdWx0IGZ1bmN0aW9uIFdvcmtiZW5jaExheW91dCgpIHtcbiAgcmV0dXJuIChcbiAgICA8ZGl2IGNzcz17d29ya2JlbmNoU3R5bGV9PlxuICAgICAgPGhlYWRlciBjc3M9e2hlYWRlclN0eWxlfT5cbiAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC50aXRsZWJhclwiIC8+XG4gICAgICA8L2hlYWRlcj5cblxuICAgICAgPG1haW4gY3NzPXttYWluU3R5bGV9PlxuICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJob3Jpem9udGFsXCI+XG4gICAgICAgICAgPFBhbmVsIGRlZmF1bHRTaXplPXsyMH0gbWluU2l6ZT17MTV9PlxuICAgICAgICAgICAgey8qIOS9oOWPr+S7peebtOaOpeWcqCBWaWV3UmVuZGVyZXIg5LiK5YaZIGNzcyBwcm9wICovfVxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBcbiAgICAgICAgICAgICAgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc2lkZWJhclwiIFxuICAgICAgICAgICAgICBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGRpc3BsYXk6IGZsZXg7IGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47IGdhcDogMXJlbTsgZmxleC1ncm93OiAxO2B9IFxuICAgICAgICAgICAgLz5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgIDxQYW5lbFJlc2l6ZUhhbmRsZSBjc3M9e3Jlc2l6ZUhhbmRsZVN0eWxlfSBzdHlsZT17eyB3aWR0aDogJzRweCcgfX0gLz5cbiAgICAgICAgICBcbiAgICAgICAgICA8UGFuZWw+XG4gICAgICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJ2ZXJ0aWNhbFwiPlxuICAgICAgICAgICAgICA8UGFuZWwgZGVmYXVsdFNpemU9ezc1fSBtaW5TaXplPXs1MH0gY3NzPXtwYW5lbFN0eWxlfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLm1haW4uY29udGFpbmVyXCI+XG4gICAgICAgICAgICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGp1c3RpZnktY29udGVudDogY2VudGVyOyBoZWlnaHQ6IDEwMCU7IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5NYWluIENvbnRlbnQgQXJlYTwvcD5cbiAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgIDwvVmlld1JlbmRlcmVyPlxuICAgICAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgICAgICA8UGFuZWxSZXNpemVIYW5kbGUgY3NzPXtyZXNpemVIYW5kbGVTdHlsZX0gc3R5bGU9e3sgaGVpZ2h0OiAnNHB4JyB9fS8+XG4gICAgICAgICAgICAgIDxQYW5lbCBkZWZhdWx0U2l6ZT17MjV9IG1pblNpemU9ezEwfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLnBhbmVsLmNvbnRhaW5lclwiPlxuICAgICAgICAgICAgICAgICAgPGRpdiBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5QYW5lbCBBcmVhIChlLmcuLCBDb25zb2xlLCBUZXJtaW5hbCk8L3A+XG4gICAgICAgICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgICAgICAgICA8L1ZpZXdSZW5kZXJlcj5cbiAgICAgICAgICAgICAgPC9QYW5lbD5cbiAgICAgICAgICAgIDwvUGFuZWxHcm91cD5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICA8L1BhbmVsR3JvdXA+XG4gICAgICA8L21haW4+XG4gICAgICBcbiAgICAgIDxmb290ZXIgY3NzPXtmb290ZXJTdHlsZX0+XG4gICAgICAgIDxkaXYgY3NzPXtjc3NgZGlzcGxheTogZmxleDsgYWxpZ24taXRlbXM6IGNlbnRlcjsgZ2FwOiAxcmVtO2B9PlxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC5zdGF0dXNiYXIubGVmdFwiIC8+XG4gICAgICAgIDwvZGl2PlxuICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGdhcDogMXJlbTtgfT5cbiAgICAgICAgICAgIDxWaWV3UmVuZGVyZXIgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc3RhdHVzYmFyLnJpZ2h0XCIgLz5cbiAgICAgICAgPC9kaXY+XG4gICAgICA8L2Zvb3Rlcj5cbiAgICA8L2Rpdj5cbiAgKTtcbn1cbiJdfQ== */",
  toString: Xe
}, xg = process.env.NODE_ENV === "production" ? {
  name: "r2g86h",
  styles: "display:flex;align-items:center;gap:1rem"
} : {
  name: "zy6fgs-WorkbenchLayout",
  styles: "display:flex;align-items:center;gap:1rem;label:WorkbenchLayout;/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIi9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUErRnFCIiwiZmlsZSI6Ii9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCIsInNvdXJjZXNDb250ZW50IjpbIi8qKiBAanN4SW1wb3J0U291cmNlIEBlbW90aW9uL3JlYWN0ICovXG5pbXBvcnQgeyBjc3MgfSBmcm9tICdAZW1vdGlvbi9yZWFjdCc7XG5pbXBvcnQgUmVhY3QgZnJvbSAncmVhY3QnO1xuaW1wb3J0IHsgUGFuZWwsIFBhbmVsR3JvdXAsIFBhbmVsUmVzaXplSGFuZGxlIH0gZnJvbSAncmVhY3QtcmVzaXphYmxlLXBhbmVscyc7XG5pbXBvcnQgVmlld1JlbmRlcmVyIGZyb20gJy4vVmlld1JlbmRlcmVyJztcblxuLy8g5L2/55SoIEVtb3Rpb24g5a6a5LmJ5qC35byPXG5jb25zdCB3b3JrYmVuY2hTdHlsZSA9IGNzc2BcbiAgZGlzcGxheTogZmxleDtcbiAgZmxleC1kaXJlY3Rpb246IGNvbHVtbjtcbiAgaGVpZ2h0OiAxMDB2aDtcbiAgd2lkdGg6IDEwMHZ3O1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMWYyOTM3OyAvLyBiZy1ncmF5LTgwMFxuICBjb2xvcjogI2QxZDVkYjsgLy8gdGV4dC1ncmF5LTIwMFxuICBmb250LWZhbWlseTogc2Fucy1zZXJpZjtcbmA7XG5cbmNvbnN0IGhlYWRlclN0eWxlID0gY3NzYFxuICBoZWlnaHQ6IDJyZW07IC8qIGgtOCAqL1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICBmbGV4LXNocmluazogMDtcbmA7XG5cbmNvbnN0IG1haW5TdHlsZSA9IGNzc2BcbiAgZmxleC1ncm93OiAxO1xuICBtaW4taGVpZ2h0OiAwO1xuYDtcblxuY29uc3QgcGFuZWxTdHlsZSA9IGNzc2BcbiAgYmFja2dyb3VuZC1jb2xvcjogIzM3NDE1MTsgLyogYmctZ3JheS03MDAgKi9cbmA7XG5cbmNvbnN0IHJlc2l6ZUhhbmRsZVN0eWxlID0gY3NzYFxuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICB0cmFuc2l0aW9uOiBiYWNrZ3JvdW5kLWNvbG9yIDAuMnM7XG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiaG92ZXJcIl0sXG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiZHJhZ1wiXSB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogIzNiODJmNjsgLyogaG92ZXI6YmctYmx1ZS01MDAgKi9cbiAgfVxuYDtcblxuY29uc3QgZm9vdGVyU3R5bGUgPSBjc3NgXG4gIGhlaWdodDogMS41cmVtOyAvKiBoLTYgKi9cbiAgYmFja2dyb3VuZC1jb2xvcjogIzI1NjNlYjsgLyogYmctYmx1ZS02MDAgKi9cbiAgZmxleC1zaHJpbms6IDA7XG4gIGRpc3BsYXk6IGZsZXg7XG4gIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gIGp1c3RpZnktY29udGVudDogc3BhY2UtYmV0d2VlbjtcbiAgcGFkZGluZzogMCAxcmVtOyAvKiBweC00ICovXG4gIGZvbnQtc2l6ZTogMC43NXJlbTsgLyogdGV4dC14cyAqL1xuICBjb2xvcjogd2hpdGU7XG5gO1xuXG4vLyDnu4Tku7blrprkuYlcbmV4cG9ydCBkZWZhdWx0IGZ1bmN0aW9uIFdvcmtiZW5jaExheW91dCgpIHtcbiAgcmV0dXJuIChcbiAgICA8ZGl2IGNzcz17d29ya2JlbmNoU3R5bGV9PlxuICAgICAgPGhlYWRlciBjc3M9e2hlYWRlclN0eWxlfT5cbiAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC50aXRsZWJhclwiIC8+XG4gICAgICA8L2hlYWRlcj5cblxuICAgICAgPG1haW4gY3NzPXttYWluU3R5bGV9PlxuICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJob3Jpem9udGFsXCI+XG4gICAgICAgICAgPFBhbmVsIGRlZmF1bHRTaXplPXsyMH0gbWluU2l6ZT17MTV9PlxuICAgICAgICAgICAgey8qIOS9oOWPr+S7peebtOaOpeWcqCBWaWV3UmVuZGVyZXIg5LiK5YaZIGNzcyBwcm9wICovfVxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBcbiAgICAgICAgICAgICAgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc2lkZWJhclwiIFxuICAgICAgICAgICAgICBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGRpc3BsYXk6IGZsZXg7IGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47IGdhcDogMXJlbTsgZmxleC1ncm93OiAxO2B9IFxuICAgICAgICAgICAgLz5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgIDxQYW5lbFJlc2l6ZUhhbmRsZSBjc3M9e3Jlc2l6ZUhhbmRsZVN0eWxlfSBzdHlsZT17eyB3aWR0aDogJzRweCcgfX0gLz5cbiAgICAgICAgICBcbiAgICAgICAgICA8UGFuZWw+XG4gICAgICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJ2ZXJ0aWNhbFwiPlxuICAgICAgICAgICAgICA8UGFuZWwgZGVmYXVsdFNpemU9ezc1fSBtaW5TaXplPXs1MH0gY3NzPXtwYW5lbFN0eWxlfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLm1haW4uY29udGFpbmVyXCI+XG4gICAgICAgICAgICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGp1c3RpZnktY29udGVudDogY2VudGVyOyBoZWlnaHQ6IDEwMCU7IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5NYWluIENvbnRlbnQgQXJlYTwvcD5cbiAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgIDwvVmlld1JlbmRlcmVyPlxuICAgICAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgICAgICA8UGFuZWxSZXNpemVIYW5kbGUgY3NzPXtyZXNpemVIYW5kbGVTdHlsZX0gc3R5bGU9e3sgaGVpZ2h0OiAnNHB4JyB9fS8+XG4gICAgICAgICAgICAgIDxQYW5lbCBkZWZhdWx0U2l6ZT17MjV9IG1pblNpemU9ezEwfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLnBhbmVsLmNvbnRhaW5lclwiPlxuICAgICAgICAgICAgICAgICAgPGRpdiBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5QYW5lbCBBcmVhIChlLmcuLCBDb25zb2xlLCBUZXJtaW5hbCk8L3A+XG4gICAgICAgICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgICAgICAgICA8L1ZpZXdSZW5kZXJlcj5cbiAgICAgICAgICAgICAgPC9QYW5lbD5cbiAgICAgICAgICAgIDwvUGFuZWxHcm91cD5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICA8L1BhbmVsR3JvdXA+XG4gICAgICA8L21haW4+XG4gICAgICBcbiAgICAgIDxmb290ZXIgY3NzPXtmb290ZXJTdHlsZX0+XG4gICAgICAgIDxkaXYgY3NzPXtjc3NgZGlzcGxheTogZmxleDsgYWxpZ24taXRlbXM6IGNlbnRlcjsgZ2FwOiAxcmVtO2B9PlxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC5zdGF0dXNiYXIubGVmdFwiIC8+XG4gICAgICAgIDwvZGl2PlxuICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGdhcDogMXJlbTtgfT5cbiAgICAgICAgICAgIDxWaWV3UmVuZGVyZXIgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc3RhdHVzYmFyLnJpZ2h0XCIgLz5cbiAgICAgICAgPC9kaXY+XG4gICAgICA8L2Zvb3Rlcj5cbiAgICA8L2Rpdj5cbiAgKTtcbn1cbiJdfQ== */",
  toString: Xe
}, vg = process.env.NODE_ENV === "production" ? {
  name: "5pc8b1",
  styles: "padding:0.5rem;color:#6b7280"
} : {
  name: "iko13a-WorkbenchLayout",
  styles: "padding:0.5rem;color:#6b7280;label:WorkbenchLayout;/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIi9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFvRitCIiwiZmlsZSI6Ii9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCIsInNvdXJjZXNDb250ZW50IjpbIi8qKiBAanN4SW1wb3J0U291cmNlIEBlbW90aW9uL3JlYWN0ICovXG5pbXBvcnQgeyBjc3MgfSBmcm9tICdAZW1vdGlvbi9yZWFjdCc7XG5pbXBvcnQgUmVhY3QgZnJvbSAncmVhY3QnO1xuaW1wb3J0IHsgUGFuZWwsIFBhbmVsR3JvdXAsIFBhbmVsUmVzaXplSGFuZGxlIH0gZnJvbSAncmVhY3QtcmVzaXphYmxlLXBhbmVscyc7XG5pbXBvcnQgVmlld1JlbmRlcmVyIGZyb20gJy4vVmlld1JlbmRlcmVyJztcblxuLy8g5L2/55SoIEVtb3Rpb24g5a6a5LmJ5qC35byPXG5jb25zdCB3b3JrYmVuY2hTdHlsZSA9IGNzc2BcbiAgZGlzcGxheTogZmxleDtcbiAgZmxleC1kaXJlY3Rpb246IGNvbHVtbjtcbiAgaGVpZ2h0OiAxMDB2aDtcbiAgd2lkdGg6IDEwMHZ3O1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMWYyOTM3OyAvLyBiZy1ncmF5LTgwMFxuICBjb2xvcjogI2QxZDVkYjsgLy8gdGV4dC1ncmF5LTIwMFxuICBmb250LWZhbWlseTogc2Fucy1zZXJpZjtcbmA7XG5cbmNvbnN0IGhlYWRlclN0eWxlID0gY3NzYFxuICBoZWlnaHQ6IDJyZW07IC8qIGgtOCAqL1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICBmbGV4LXNocmluazogMDtcbmA7XG5cbmNvbnN0IG1haW5TdHlsZSA9IGNzc2BcbiAgZmxleC1ncm93OiAxO1xuICBtaW4taGVpZ2h0OiAwO1xuYDtcblxuY29uc3QgcGFuZWxTdHlsZSA9IGNzc2BcbiAgYmFja2dyb3VuZC1jb2xvcjogIzM3NDE1MTsgLyogYmctZ3JheS03MDAgKi9cbmA7XG5cbmNvbnN0IHJlc2l6ZUhhbmRsZVN0eWxlID0gY3NzYFxuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICB0cmFuc2l0aW9uOiBiYWNrZ3JvdW5kLWNvbG9yIDAuMnM7XG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiaG92ZXJcIl0sXG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiZHJhZ1wiXSB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogIzNiODJmNjsgLyogaG92ZXI6YmctYmx1ZS01MDAgKi9cbiAgfVxuYDtcblxuY29uc3QgZm9vdGVyU3R5bGUgPSBjc3NgXG4gIGhlaWdodDogMS41cmVtOyAvKiBoLTYgKi9cbiAgYmFja2dyb3VuZC1jb2xvcjogIzI1NjNlYjsgLyogYmctYmx1ZS02MDAgKi9cbiAgZmxleC1zaHJpbms6IDA7XG4gIGRpc3BsYXk6IGZsZXg7XG4gIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gIGp1c3RpZnktY29udGVudDogc3BhY2UtYmV0d2VlbjtcbiAgcGFkZGluZzogMCAxcmVtOyAvKiBweC00ICovXG4gIGZvbnQtc2l6ZTogMC43NXJlbTsgLyogdGV4dC14cyAqL1xuICBjb2xvcjogd2hpdGU7XG5gO1xuXG4vLyDnu4Tku7blrprkuYlcbmV4cG9ydCBkZWZhdWx0IGZ1bmN0aW9uIFdvcmtiZW5jaExheW91dCgpIHtcbiAgcmV0dXJuIChcbiAgICA8ZGl2IGNzcz17d29ya2JlbmNoU3R5bGV9PlxuICAgICAgPGhlYWRlciBjc3M9e2hlYWRlclN0eWxlfT5cbiAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC50aXRsZWJhclwiIC8+XG4gICAgICA8L2hlYWRlcj5cblxuICAgICAgPG1haW4gY3NzPXttYWluU3R5bGV9PlxuICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJob3Jpem9udGFsXCI+XG4gICAgICAgICAgPFBhbmVsIGRlZmF1bHRTaXplPXsyMH0gbWluU2l6ZT17MTV9PlxuICAgICAgICAgICAgey8qIOS9oOWPr+S7peebtOaOpeWcqCBWaWV3UmVuZGVyZXIg5LiK5YaZIGNzcyBwcm9wICovfVxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBcbiAgICAgICAgICAgICAgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc2lkZWJhclwiIFxuICAgICAgICAgICAgICBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGRpc3BsYXk6IGZsZXg7IGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47IGdhcDogMXJlbTsgZmxleC1ncm93OiAxO2B9IFxuICAgICAgICAgICAgLz5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgIDxQYW5lbFJlc2l6ZUhhbmRsZSBjc3M9e3Jlc2l6ZUhhbmRsZVN0eWxlfSBzdHlsZT17eyB3aWR0aDogJzRweCcgfX0gLz5cbiAgICAgICAgICBcbiAgICAgICAgICA8UGFuZWw+XG4gICAgICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJ2ZXJ0aWNhbFwiPlxuICAgICAgICAgICAgICA8UGFuZWwgZGVmYXVsdFNpemU9ezc1fSBtaW5TaXplPXs1MH0gY3NzPXtwYW5lbFN0eWxlfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLm1haW4uY29udGFpbmVyXCI+XG4gICAgICAgICAgICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGp1c3RpZnktY29udGVudDogY2VudGVyOyBoZWlnaHQ6IDEwMCU7IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5NYWluIENvbnRlbnQgQXJlYTwvcD5cbiAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgIDwvVmlld1JlbmRlcmVyPlxuICAgICAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgICAgICA8UGFuZWxSZXNpemVIYW5kbGUgY3NzPXtyZXNpemVIYW5kbGVTdHlsZX0gc3R5bGU9e3sgaGVpZ2h0OiAnNHB4JyB9fS8+XG4gICAgICAgICAgICAgIDxQYW5lbCBkZWZhdWx0U2l6ZT17MjV9IG1pblNpemU9ezEwfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLnBhbmVsLmNvbnRhaW5lclwiPlxuICAgICAgICAgICAgICAgICAgPGRpdiBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5QYW5lbCBBcmVhIChlLmcuLCBDb25zb2xlLCBUZXJtaW5hbCk8L3A+XG4gICAgICAgICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgICAgICAgICA8L1ZpZXdSZW5kZXJlcj5cbiAgICAgICAgICAgICAgPC9QYW5lbD5cbiAgICAgICAgICAgIDwvUGFuZWxHcm91cD5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICA8L1BhbmVsR3JvdXA+XG4gICAgICA8L21haW4+XG4gICAgICBcbiAgICAgIDxmb290ZXIgY3NzPXtmb290ZXJTdHlsZX0+XG4gICAgICAgIDxkaXYgY3NzPXtjc3NgZGlzcGxheTogZmxleDsgYWxpZ24taXRlbXM6IGNlbnRlcjsgZ2FwOiAxcmVtO2B9PlxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC5zdGF0dXNiYXIubGVmdFwiIC8+XG4gICAgICAgIDwvZGl2PlxuICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGdhcDogMXJlbTtgfT5cbiAgICAgICAgICAgIDxWaWV3UmVuZGVyZXIgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc3RhdHVzYmFyLnJpZ2h0XCIgLz5cbiAgICAgICAgPC9kaXY+XG4gICAgICA8L2Zvb3Rlcj5cbiAgICA8L2Rpdj5cbiAgKTtcbn1cbiJdfQ== */",
  toString: Xe
}, Vg = process.env.NODE_ENV === "production" ? {
  name: "12yzc4e",
  styles: "display:flex;align-items:center;justify-content:center;height:100%;color:#6b7280"
} : {
  name: "ubptj0-WorkbenchLayout",
  styles: "display:flex;align-items:center;justify-content:center;height:100%;color:#6b7280;label:WorkbenchLayout;/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIi9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUE0RStCIiwiZmlsZSI6Ii9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCIsInNvdXJjZXNDb250ZW50IjpbIi8qKiBAanN4SW1wb3J0U291cmNlIEBlbW90aW9uL3JlYWN0ICovXG5pbXBvcnQgeyBjc3MgfSBmcm9tICdAZW1vdGlvbi9yZWFjdCc7XG5pbXBvcnQgUmVhY3QgZnJvbSAncmVhY3QnO1xuaW1wb3J0IHsgUGFuZWwsIFBhbmVsR3JvdXAsIFBhbmVsUmVzaXplSGFuZGxlIH0gZnJvbSAncmVhY3QtcmVzaXphYmxlLXBhbmVscyc7XG5pbXBvcnQgVmlld1JlbmRlcmVyIGZyb20gJy4vVmlld1JlbmRlcmVyJztcblxuLy8g5L2/55SoIEVtb3Rpb24g5a6a5LmJ5qC35byPXG5jb25zdCB3b3JrYmVuY2hTdHlsZSA9IGNzc2BcbiAgZGlzcGxheTogZmxleDtcbiAgZmxleC1kaXJlY3Rpb246IGNvbHVtbjtcbiAgaGVpZ2h0OiAxMDB2aDtcbiAgd2lkdGg6IDEwMHZ3O1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMWYyOTM3OyAvLyBiZy1ncmF5LTgwMFxuICBjb2xvcjogI2QxZDVkYjsgLy8gdGV4dC1ncmF5LTIwMFxuICBmb250LWZhbWlseTogc2Fucy1zZXJpZjtcbmA7XG5cbmNvbnN0IGhlYWRlclN0eWxlID0gY3NzYFxuICBoZWlnaHQ6IDJyZW07IC8qIGgtOCAqL1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICBmbGV4LXNocmluazogMDtcbmA7XG5cbmNvbnN0IG1haW5TdHlsZSA9IGNzc2BcbiAgZmxleC1ncm93OiAxO1xuICBtaW4taGVpZ2h0OiAwO1xuYDtcblxuY29uc3QgcGFuZWxTdHlsZSA9IGNzc2BcbiAgYmFja2dyb3VuZC1jb2xvcjogIzM3NDE1MTsgLyogYmctZ3JheS03MDAgKi9cbmA7XG5cbmNvbnN0IHJlc2l6ZUhhbmRsZVN0eWxlID0gY3NzYFxuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICB0cmFuc2l0aW9uOiBiYWNrZ3JvdW5kLWNvbG9yIDAuMnM7XG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiaG92ZXJcIl0sXG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiZHJhZ1wiXSB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogIzNiODJmNjsgLyogaG92ZXI6YmctYmx1ZS01MDAgKi9cbiAgfVxuYDtcblxuY29uc3QgZm9vdGVyU3R5bGUgPSBjc3NgXG4gIGhlaWdodDogMS41cmVtOyAvKiBoLTYgKi9cbiAgYmFja2dyb3VuZC1jb2xvcjogIzI1NjNlYjsgLyogYmctYmx1ZS02MDAgKi9cbiAgZmxleC1zaHJpbms6IDA7XG4gIGRpc3BsYXk6IGZsZXg7XG4gIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gIGp1c3RpZnktY29udGVudDogc3BhY2UtYmV0d2VlbjtcbiAgcGFkZGluZzogMCAxcmVtOyAvKiBweC00ICovXG4gIGZvbnQtc2l6ZTogMC43NXJlbTsgLyogdGV4dC14cyAqL1xuICBjb2xvcjogd2hpdGU7XG5gO1xuXG4vLyDnu4Tku7blrprkuYlcbmV4cG9ydCBkZWZhdWx0IGZ1bmN0aW9uIFdvcmtiZW5jaExheW91dCgpIHtcbiAgcmV0dXJuIChcbiAgICA8ZGl2IGNzcz17d29ya2JlbmNoU3R5bGV9PlxuICAgICAgPGhlYWRlciBjc3M9e2hlYWRlclN0eWxlfT5cbiAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC50aXRsZWJhclwiIC8+XG4gICAgICA8L2hlYWRlcj5cblxuICAgICAgPG1haW4gY3NzPXttYWluU3R5bGV9PlxuICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJob3Jpem9udGFsXCI+XG4gICAgICAgICAgPFBhbmVsIGRlZmF1bHRTaXplPXsyMH0gbWluU2l6ZT17MTV9PlxuICAgICAgICAgICAgey8qIOS9oOWPr+S7peebtOaOpeWcqCBWaWV3UmVuZGVyZXIg5LiK5YaZIGNzcyBwcm9wICovfVxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBcbiAgICAgICAgICAgICAgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc2lkZWJhclwiIFxuICAgICAgICAgICAgICBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGRpc3BsYXk6IGZsZXg7IGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47IGdhcDogMXJlbTsgZmxleC1ncm93OiAxO2B9IFxuICAgICAgICAgICAgLz5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgIDxQYW5lbFJlc2l6ZUhhbmRsZSBjc3M9e3Jlc2l6ZUhhbmRsZVN0eWxlfSBzdHlsZT17eyB3aWR0aDogJzRweCcgfX0gLz5cbiAgICAgICAgICBcbiAgICAgICAgICA8UGFuZWw+XG4gICAgICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJ2ZXJ0aWNhbFwiPlxuICAgICAgICAgICAgICA8UGFuZWwgZGVmYXVsdFNpemU9ezc1fSBtaW5TaXplPXs1MH0gY3NzPXtwYW5lbFN0eWxlfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLm1haW4uY29udGFpbmVyXCI+XG4gICAgICAgICAgICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGp1c3RpZnktY29udGVudDogY2VudGVyOyBoZWlnaHQ6IDEwMCU7IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5NYWluIENvbnRlbnQgQXJlYTwvcD5cbiAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgIDwvVmlld1JlbmRlcmVyPlxuICAgICAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgICAgICA8UGFuZWxSZXNpemVIYW5kbGUgY3NzPXtyZXNpemVIYW5kbGVTdHlsZX0gc3R5bGU9e3sgaGVpZ2h0OiAnNHB4JyB9fS8+XG4gICAgICAgICAgICAgIDxQYW5lbCBkZWZhdWx0U2l6ZT17MjV9IG1pblNpemU9ezEwfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLnBhbmVsLmNvbnRhaW5lclwiPlxuICAgICAgICAgICAgICAgICAgPGRpdiBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5QYW5lbCBBcmVhIChlLmcuLCBDb25zb2xlLCBUZXJtaW5hbCk8L3A+XG4gICAgICAgICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgICAgICAgICA8L1ZpZXdSZW5kZXJlcj5cbiAgICAgICAgICAgICAgPC9QYW5lbD5cbiAgICAgICAgICAgIDwvUGFuZWxHcm91cD5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICA8L1BhbmVsR3JvdXA+XG4gICAgICA8L21haW4+XG4gICAgICBcbiAgICAgIDxmb290ZXIgY3NzPXtmb290ZXJTdHlsZX0+XG4gICAgICAgIDxkaXYgY3NzPXtjc3NgZGlzcGxheTogZmxleDsgYWxpZ24taXRlbXM6IGNlbnRlcjsgZ2FwOiAxcmVtO2B9PlxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC5zdGF0dXNiYXIubGVmdFwiIC8+XG4gICAgICAgIDwvZGl2PlxuICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGdhcDogMXJlbTtgfT5cbiAgICAgICAgICAgIDxWaWV3UmVuZGVyZXIgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc3RhdHVzYmFyLnJpZ2h0XCIgLz5cbiAgICAgICAgPC9kaXY+XG4gICAgICA8L2Zvb3Rlcj5cbiAgICA8L2Rpdj5cbiAgKTtcbn1cbiJdfQ== */",
  toString: Xe
}, hg = process.env.NODE_ENV === "production" ? {
  name: "fhak9r",
  styles: "padding:0.5rem;display:flex;flex-direction:column;gap:1rem;flex-grow:1"
} : {
  name: "hvr18r-WorkbenchLayout",
  styles: "padding:0.5rem;display:flex;flex-direction:column;gap:1rem;flex-grow:1;label:WorkbenchLayout;/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIi9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiQUFtRXNCIiwiZmlsZSI6Ii9Vc2Vycy9uaXVyeC9IZXZuby9wbHVnaW5zL2NvcmVfbGF5b3V0L2NvbXBvbmVudHMvV29ya2JlbmNoTGF5b3V0LnRzeCIsInNvdXJjZXNDb250ZW50IjpbIi8qKiBAanN4SW1wb3J0U291cmNlIEBlbW90aW9uL3JlYWN0ICovXG5pbXBvcnQgeyBjc3MgfSBmcm9tICdAZW1vdGlvbi9yZWFjdCc7XG5pbXBvcnQgUmVhY3QgZnJvbSAncmVhY3QnO1xuaW1wb3J0IHsgUGFuZWwsIFBhbmVsR3JvdXAsIFBhbmVsUmVzaXplSGFuZGxlIH0gZnJvbSAncmVhY3QtcmVzaXphYmxlLXBhbmVscyc7XG5pbXBvcnQgVmlld1JlbmRlcmVyIGZyb20gJy4vVmlld1JlbmRlcmVyJztcblxuLy8g5L2/55SoIEVtb3Rpb24g5a6a5LmJ5qC35byPXG5jb25zdCB3b3JrYmVuY2hTdHlsZSA9IGNzc2BcbiAgZGlzcGxheTogZmxleDtcbiAgZmxleC1kaXJlY3Rpb246IGNvbHVtbjtcbiAgaGVpZ2h0OiAxMDB2aDtcbiAgd2lkdGg6IDEwMHZ3O1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMWYyOTM3OyAvLyBiZy1ncmF5LTgwMFxuICBjb2xvcjogI2QxZDVkYjsgLy8gdGV4dC1ncmF5LTIwMFxuICBmb250LWZhbWlseTogc2Fucy1zZXJpZjtcbmA7XG5cbmNvbnN0IGhlYWRlclN0eWxlID0gY3NzYFxuICBoZWlnaHQ6IDJyZW07IC8qIGgtOCAqL1xuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICBmbGV4LXNocmluazogMDtcbmA7XG5cbmNvbnN0IG1haW5TdHlsZSA9IGNzc2BcbiAgZmxleC1ncm93OiAxO1xuICBtaW4taGVpZ2h0OiAwO1xuYDtcblxuY29uc3QgcGFuZWxTdHlsZSA9IGNzc2BcbiAgYmFja2dyb3VuZC1jb2xvcjogIzM3NDE1MTsgLyogYmctZ3JheS03MDAgKi9cbmA7XG5cbmNvbnN0IHJlc2l6ZUhhbmRsZVN0eWxlID0gY3NzYFxuICBiYWNrZ3JvdW5kLWNvbG9yOiAjMTExODI3OyAvKiBiZy1ncmF5LTkwMCAqL1xuICB0cmFuc2l0aW9uOiBiYWNrZ3JvdW5kLWNvbG9yIDAuMnM7XG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiaG92ZXJcIl0sXG4gICZbZGF0YS1yZXNpemUtaGFuZGxlLXN0YXRlPVwiZHJhZ1wiXSB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogIzNiODJmNjsgLyogaG92ZXI6YmctYmx1ZS01MDAgKi9cbiAgfVxuYDtcblxuY29uc3QgZm9vdGVyU3R5bGUgPSBjc3NgXG4gIGhlaWdodDogMS41cmVtOyAvKiBoLTYgKi9cbiAgYmFja2dyb3VuZC1jb2xvcjogIzI1NjNlYjsgLyogYmctYmx1ZS02MDAgKi9cbiAgZmxleC1zaHJpbms6IDA7XG4gIGRpc3BsYXk6IGZsZXg7XG4gIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gIGp1c3RpZnktY29udGVudDogc3BhY2UtYmV0d2VlbjtcbiAgcGFkZGluZzogMCAxcmVtOyAvKiBweC00ICovXG4gIGZvbnQtc2l6ZTogMC43NXJlbTsgLyogdGV4dC14cyAqL1xuICBjb2xvcjogd2hpdGU7XG5gO1xuXG4vLyDnu4Tku7blrprkuYlcbmV4cG9ydCBkZWZhdWx0IGZ1bmN0aW9uIFdvcmtiZW5jaExheW91dCgpIHtcbiAgcmV0dXJuIChcbiAgICA8ZGl2IGNzcz17d29ya2JlbmNoU3R5bGV9PlxuICAgICAgPGhlYWRlciBjc3M9e2hlYWRlclN0eWxlfT5cbiAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC50aXRsZWJhclwiIC8+XG4gICAgICA8L2hlYWRlcj5cblxuICAgICAgPG1haW4gY3NzPXttYWluU3R5bGV9PlxuICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJob3Jpem9udGFsXCI+XG4gICAgICAgICAgPFBhbmVsIGRlZmF1bHRTaXplPXsyMH0gbWluU2l6ZT17MTV9PlxuICAgICAgICAgICAgey8qIOS9oOWPr+S7peebtOaOpeWcqCBWaWV3UmVuZGVyZXIg5LiK5YaZIGNzcyBwcm9wICovfVxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBcbiAgICAgICAgICAgICAgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc2lkZWJhclwiIFxuICAgICAgICAgICAgICBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGRpc3BsYXk6IGZsZXg7IGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47IGdhcDogMXJlbTsgZmxleC1ncm93OiAxO2B9IFxuICAgICAgICAgICAgLz5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgIDxQYW5lbFJlc2l6ZUhhbmRsZSBjc3M9e3Jlc2l6ZUhhbmRsZVN0eWxlfSBzdHlsZT17eyB3aWR0aDogJzRweCcgfX0gLz5cbiAgICAgICAgICBcbiAgICAgICAgICA8UGFuZWw+XG4gICAgICAgICAgICA8UGFuZWxHcm91cCBkaXJlY3Rpb249XCJ2ZXJ0aWNhbFwiPlxuICAgICAgICAgICAgICA8UGFuZWwgZGVmYXVsdFNpemU9ezc1fSBtaW5TaXplPXs1MH0gY3NzPXtwYW5lbFN0eWxlfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLm1haW4uY29udGFpbmVyXCI+XG4gICAgICAgICAgICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGp1c3RpZnktY29udGVudDogY2VudGVyOyBoZWlnaHQ6IDEwMCU7IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5NYWluIENvbnRlbnQgQXJlYTwvcD5cbiAgICAgICAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgICAgICAgIDwvVmlld1JlbmRlcmVyPlxuICAgICAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICAgICAgICA8UGFuZWxSZXNpemVIYW5kbGUgY3NzPXtyZXNpemVIYW5kbGVTdHlsZX0gc3R5bGU9e3sgaGVpZ2h0OiAnNHB4JyB9fS8+XG4gICAgICAgICAgICAgIDxQYW5lbCBkZWZhdWx0U2l6ZT17MjV9IG1pblNpemU9ezEwfT5cbiAgICAgICAgICAgICAgICA8Vmlld1JlbmRlcmVyIGNvbnRyaWJ1dGlvblBvaW50PVwid29ya2JlbmNoLnBhbmVsLmNvbnRhaW5lclwiPlxuICAgICAgICAgICAgICAgICAgPGRpdiBjc3M9e2Nzc2BwYWRkaW5nOiAwLjVyZW07IGNvbG9yOiAjNmI3MjgwO2B9PlxuICAgICAgICAgICAgICAgICAgICA8cD5QYW5lbCBBcmVhIChlLmcuLCBDb25zb2xlLCBUZXJtaW5hbCk8L3A+XG4gICAgICAgICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgICAgICAgICA8L1ZpZXdSZW5kZXJlcj5cbiAgICAgICAgICAgICAgPC9QYW5lbD5cbiAgICAgICAgICAgIDwvUGFuZWxHcm91cD5cbiAgICAgICAgICA8L1BhbmVsPlxuICAgICAgICA8L1BhbmVsR3JvdXA+XG4gICAgICA8L21haW4+XG4gICAgICBcbiAgICAgIDxmb290ZXIgY3NzPXtmb290ZXJTdHlsZX0+XG4gICAgICAgIDxkaXYgY3NzPXtjc3NgZGlzcGxheTogZmxleDsgYWxpZ24taXRlbXM6IGNlbnRlcjsgZ2FwOiAxcmVtO2B9PlxuICAgICAgICAgICAgPFZpZXdSZW5kZXJlciBjb250cmlidXRpb25Qb2ludD1cIndvcmtiZW5jaC5zdGF0dXNiYXIubGVmdFwiIC8+XG4gICAgICAgIDwvZGl2PlxuICAgICAgICA8ZGl2IGNzcz17Y3NzYGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGdhcDogMXJlbTtgfT5cbiAgICAgICAgICAgIDxWaWV3UmVuZGVyZXIgY29udHJpYnV0aW9uUG9pbnQ9XCJ3b3JrYmVuY2guc3RhdHVzYmFyLnJpZ2h0XCIgLz5cbiAgICAgICAgPC9kaXY+XG4gICAgICA8L2Zvb3Rlcj5cbiAgICA8L2Rpdj5cbiAgKTtcbn1cbiJdfQ== */",
  toString: Xe
};
function Yg() {
  return /* @__PURE__ */ Zn("div", { css: Gg, children: [
    /* @__PURE__ */ _("header", { css: fg, children: /* @__PURE__ */ _(Qe, { contributionPoint: "workbench.titlebar" }) }),
    /* @__PURE__ */ _("main", { css: yg, children: /* @__PURE__ */ Zn(nt, { direction: "horizontal", children: [
      /* @__PURE__ */ _(In, { defaultSize: 20, minSize: 15, children: /* @__PURE__ */ _(Qe, { contributionPoint: "workbench.sidebar", css: hg }) }),
      /* @__PURE__ */ _(tt, { css: Tt, style: {
        width: "4px"
      } }),
      /* @__PURE__ */ _(In, { children: /* @__PURE__ */ Zn(nt, { direction: "vertical", children: [
        /* @__PURE__ */ _(In, { defaultSize: 75, minSize: 50, css: Wg, children: /* @__PURE__ */ _(Qe, { contributionPoint: "workbench.main.container", children: /* @__PURE__ */ _("div", { css: Vg, children: /* @__PURE__ */ _("p", { children: "Main Content Area" }) }) }) }),
        /* @__PURE__ */ _(tt, { css: Tt, style: {
          height: "4px"
        } }),
        /* @__PURE__ */ _(In, { defaultSize: 25, minSize: 10, children: /* @__PURE__ */ _(Qe, { contributionPoint: "workbench.panel.container", children: /* @__PURE__ */ _("div", { css: vg, children: /* @__PURE__ */ _("p", { children: "Panel Area (e.g., Console, Terminal)" }) }) }) })
      ] }) })
    ] }) }),
    /* @__PURE__ */ Zn("footer", { css: pg, children: [
      /* @__PURE__ */ _("div", { css: xg, children: /* @__PURE__ */ _(Qe, { contributionPoint: "workbench.statusbar.left" }) }),
      /* @__PURE__ */ _("div", { css: Xg, children: /* @__PURE__ */ _(Qe, { contributionPoint: "workbench.statusbar.right" }) })
    ] })
  ] });
}
class Ng {
  focusPanel(n) {
    Hn.bus.emit("layout:focus-panel", {
      panelId: n
    }), console.log(`[core-layout] Focusing panel: ${n}`);
  }
  toggleSidebar() {
    Hn.bus.emit("layout:toggle-sidebar"), console.log("[core-layout] Toggling sidebar visibility");
  }
}
const Rg = Tc({
  /**
   * 在 onLoad 阶段，插件应该只做最基本的事情：注册自己。
   * 它不应该期望其他插件或服务已经存在。
   */
  onLoad: (e) => {
    console.log(`[core-layout] Plugin loaded. Priority: ${e.getManifest().config.priority}.`), e.registerComponent("WorkbenchRoot", Yg);
  },
  /**
   * 在 onActivate 阶段，所有插件的 onLoad 都已完成。
   * 这是注册需要依赖其他服务的服务的安全时机。
   */
  onActivate: (e) => {
    console.log("[core-layout] Plugin activated.");
    const n = new Ng();
    Hn.registry.register("layoutService", n);
  }
});
export {
  Rg as default
};
