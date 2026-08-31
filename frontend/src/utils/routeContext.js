/**
 * routeContext.js — Objective CB-5
 * Reads pathname + maps to topic; full URL is sent with every chat request.
 */

const ROUTE_MAP = [
  { match: /\/partial-derivatives\/2/, topic: "Partial Derivatives Part 2", detail: "higher-order partials, mixed partials, chain rule for multivariable functions" },
  { match: /\/partial-derivatives\/1/, topic: "Partial Derivatives Part 1", detail: "definition of partial derivatives, notation, geometric interpretation" },
  { match: /\/partial-derivatives/, topic: "Partial Derivatives", detail: "partial derivatives and related concepts" },
  { match: /\/vector-calculus\/2/, topic: "Vector Calculus Part 2", detail: "curl, divergence, Stokes theorem, divergence theorem" },
  { match: /\/vector-calculus\/1/, topic: "Vector Calculus Part 1", detail: "vector fields, line integrals, gradient, flux" },
  { match: /\/vector-calculus/, topic: "Vector Calculus", detail: "vector calculus topics" },
  { match: /\/limits-continuity\/2/, topic: "Limits and Continuity Part 2", detail: "continuity of multivariable functions, continuity on regions" },
  { match: /\/limits-continuity\/1/, topic: "Limits and Continuity Part 1", detail: "limits of multivariable functions, path-dependent limits" },
  { match: /\/limits-continuity/, topic: "Limits and Continuity", detail: "limits and continuity for multivariable functions" },
  { match: /\/multiple-integrals\/2/, topic: "Multiple Integrals Part 2", detail: "change of variables, Jacobians, polar, cylindrical and spherical coordinates" },
  { match: /\/multiple-integrals\/1/, topic: "Multiple Integrals Part 1", detail: "double integrals, iterated integrals, Fubini's theorem" },
  { match: /\/multiple-integrals/, topic: "Multiple Integrals", detail: "double and triple integrals" },
  { match: /\/simple-concepts\/[^/]+/, topic: "Simple Concepts (detail page)", detail: "interactive concept exploration" },
  { match: /\/simple-concepts/, topic: "Simple Concepts", detail: "functions of several variables, level curves, surfaces in 3D" },
  { match: /\/test/, topic: "Continuity Finder Tool", detail: "testing continuity of multivariable functions" },
  { match: /\/extreme/, topic: "Extreme Value Finder Tool", detail: "critical points, second derivative test, saddle points" },
  { match: /\/volumecalculator/, topic: "Volume Calculator Tool", detail: "volumes using double and triple integrals" },
  { match: /\/ai-solver/, topic: "AI Solver", detail: "symbolic computation for calculus problems" },
  { match: /\/dashboard/, topic: "Dashboard", detail: "student progress and saved work" },
  { match: /\/login/, topic: "Login", detail: "account sign-in" },
  { match: /\/signup/, topic: "Sign Up", detail: "account registration" },
  { match: /^\/$/, topic: "Home", detail: "general multivariable calculus overview" },
];

export function getPageUrl() {
  if (typeof window === "undefined") return "/";
  return window.location.pathname;
}

export function getTopicContext(pathname = getPageUrl()) {
  for (const entry of ROUTE_MAP) {
    if (entry.match.test(pathname)) {
      return { topic: entry.topic, detail: entry.detail };
    }
  }
  return { topic: "Multivariable Calculus", detail: "general multivariable calculus topics" };
}

/** Full context string injected into every LLM request */
export function getContextString(pathname = getPageUrl()) {
  const { topic, detail } = getTopicContext(pathname);
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const fullUrl = `${origin}${pathname}`;
  return (
    `The student is currently on CalcVoyager page ${pathname} (full URL: ${fullUrl}). ` +
    `Topic: "${topic}". Focus: ${detail}.`
  );
}