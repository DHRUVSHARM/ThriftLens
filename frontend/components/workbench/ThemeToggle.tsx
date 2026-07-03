"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { IconButton } from "./ui";

type Theme = "light" | "dark";
const THEME_CHANGE_EVENT = "thriftlens-theme-change";

function preferredTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  const stored = window.localStorage.getItem("thriftlens-theme");
  if (stored === "light" || stored === "dark") return stored;
  return "dark";
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  window.localStorage.setItem("thriftlens-theme", theme);
  window.dispatchEvent(new CustomEvent(THEME_CHANGE_EVENT, { detail: theme }));
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const initial = preferredTheme();
    setTheme(initial);
    document.documentElement.dataset.theme = initial;
    function handleThemeChange(event: Event) {
      const nextTheme = event instanceof CustomEvent && (event.detail === "light" || event.detail === "dark") ? event.detail : preferredTheme();
      setTheme(nextTheme);
      document.documentElement.dataset.theme = nextTheme;
    }
    window.addEventListener(THEME_CHANGE_EVENT, handleThemeChange);
    window.addEventListener("storage", handleThemeChange);
    return () => {
      window.removeEventListener(THEME_CHANGE_EVENT, handleThemeChange);
      window.removeEventListener("storage", handleThemeChange);
    };
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    applyTheme(next);
  }

  return (
    <IconButton label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} onClick={toggleTheme}>
      {theme === "dark" ? <Sun size={17} aria-hidden="true" /> : <Moon size={17} aria-hidden="true" />}
    </IconButton>
  );
}
