#!/usr/bin/env python3
"""Native Tkinter UI for Text2SQL. No web browser is required."""
from __future__ import annotations

import csv
import os
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import DOMAINS, ROOT, run_question
from src.config import Config, load_dotenv
from src.generator import Text2SQLPipeline
from src.sql_executor import dsn_for_domain, execute_readonly


DOMAIN_LABELS = {
    "01_trading_company": "Торговая компания",
    "02_legal_firm": "Юридическая фирма",
    "03_logistics_company": "Логистическая компания",
    "04_mining_company": "Горнодобывающая компания",
    "05_oil_company": "Нефтяная компания",
}

EXAMPLES = {
    "01_trading_company": ["Покажи топ-5 покупателей по общей сумме заказов", "Сколько заказов было оформлено в 2023 году?"],
    "02_legal_firm": ["Какие юристы ведут больше всего дел?", "Покажи самые крупные неоплаченные счета"],
    "03_logistics_company": ["Какие маршруты используются чаще всего?", "Покажи пять водителей с наибольшим числом рейсов"],
    "04_mining_company": ["Какие рудники добыли больше всего руды?", "Покажи оборудование, находящееся на ремонте"],
    "05_oil_company": ["Какие скважины дают наибольшую добычу?", "Покажи объём добычи по месторождениям"],
}


class DesktopApp:
    def __init__(self, root: tk.Tk):
        load_dotenv()
        self.root = root
        self.root.title("Text2SQL — вопрос к данным")
        self.root.geometry("1120x780")
        self.root.minsize(900, 650)
        self.root.option_add("*Font", "Arial 12")
        self.current_result: dict | None = None

        style = ttk.Style()
        if "aqua" in style.theme_names():
            style.theme_use("aqua")
        style.configure("Title.TLabel", font=("Arial", 24, "bold"))
        style.configure("Hint.TLabel", foreground="#52606d")
        style.configure("Run.TButton", font=("Arial", 13, "bold"), padding=(18, 9))

        configured_provider = os.getenv("LLM_PROVIDER", "").lower()
        if configured_provider not in {"openai", "ollama", "mock"}:
            configured_provider = "openai" if os.getenv("LLM_API_KEY") else "mock"
        if configured_provider == "openai" and not os.getenv("LLM_API_KEY"):
            configured_provider = "mock"
        self.provider = tk.StringVar(value=configured_provider)
        self.model = tk.StringVar(value=os.getenv("LLM_MODEL", ""))
        self.base_url = tk.StringVar(value=os.getenv("LLM_BASE_URL", ""))
        self.api_key = tk.StringVar()
        self.domain_label = tk.StringVar(value=DOMAIN_LABELS[DOMAINS[0]])
        self.status = tk.StringVar(value="Проверяю базу данных…")

        self._build()
        self._provider_changed(force_defaults=True)
        self._domain_changed()

    @property
    def domain(self) -> str:
        reverse = {label: value for value, label in DOMAIN_LABELS.items()}
        return reverse[self.domain_label.get()]

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Text2SQL", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Напишите вопрос по-русски — приложение составит SQL и найдёт ответ в базе.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(0, 14))

        settings = ttk.LabelFrame(outer, text="Настройки", padding=12)
        settings.pack(fill="x")
        for column in range(4):
            settings.columnconfigure(column, weight=1)

        ttk.Label(settings, text="Режим модели").grid(row=0, column=0, sticky="w")
        self.provider_box = ttk.Combobox(settings, textvariable=self.provider, values=("openai", "ollama", "mock"), state="readonly")
        self.provider_box.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.provider_box.bind("<<ComboboxSelected>>", lambda _event: self._provider_changed())

        ttk.Label(settings, text="Модель").grid(row=0, column=1, sticky="w")
        ttk.Entry(settings, textvariable=self.model).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Label(settings, text="Адрес API").grid(row=0, column=2, sticky="w")
        ttk.Entry(settings, textvariable=self.base_url).grid(row=1, column=2, sticky="ew", padx=8)
        ttk.Label(settings, text="API-ключ (только OpenAI)").grid(row=0, column=3, sticky="w")
        ttk.Entry(settings, textvariable=self.api_key, show="•").grid(row=1, column=3, sticky="ew", padx=(8, 0))

        query = ttk.LabelFrame(outer, text="Вопрос", padding=12)
        query.pack(fill="x", pady=12)
        query.columnconfigure(0, weight=1)

        domain_row = ttk.Frame(query)
        domain_row.grid(row=0, column=0, sticky="ew")
        ttk.Label(domain_row, text="Компания:").pack(side="left")
        self.domain_box = ttk.Combobox(domain_row, textvariable=self.domain_label, values=tuple(DOMAIN_LABELS[value] for value in DOMAINS), state="readonly", width=30)
        self.domain_box.pack(side="left", padx=8)
        self.domain_box.bind("<<ComboboxSelected>>", lambda _event: self._domain_changed())
        ttk.Label(domain_row, textvariable=self.status, style="Hint.TLabel").pack(side="left", padx=10)

        self.examples_frame = ttk.Frame(query)
        self.examples_frame.grid(row=1, column=0, sticky="ew", pady=(10, 6))
        self.question = tk.Text(query, height=4, wrap="word", font=("Arial", 13))
        self.question.grid(row=2, column=0, sticky="ew", pady=6)

        actions = ttk.Frame(query)
        actions.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        self.run_button = ttk.Button(actions, text="Найти ответ", style="Run.TButton", command=self._run)
        self.run_button.pack(side="left")
        ttk.Button(actions, text="Очистить", command=self._clear).pack(side="left", padx=8)
        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=220)
        self.progress.pack(side="right")

        self.tabs = ttk.Notebook(outer)
        self.tabs.pack(fill="both", expand=True)
        answer_tab = ttk.Frame(self.tabs, padding=10)
        table_tab = ttk.Frame(self.tabs, padding=10)
        sql_tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(answer_tab, text="Ответ")
        self.tabs.add(table_tab, text="Таблица")
        self.tabs.add(sql_tab, text="SQL и детали")

        self.answer = tk.Text(answer_tab, wrap="word", state="disabled", font=("Arial", 14))
        self.answer.pack(fill="both", expand=True)

        table_actions = ttk.Frame(table_tab)
        table_actions.pack(fill="x", pady=(0, 6))
        self.save_button = ttk.Button(table_actions, text="Сохранить CSV", command=self._save_csv, state="disabled")
        self.save_button.pack(side="right")
        table_frame = ttk.Frame(table_tab)
        table_frame.pack(fill="both", expand=True)
        self.table = ttk.Treeview(table_frame, show="headings")
        table_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        table_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=table_y.set, xscrollcommand=table_x.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        table_y.grid(row=0, column=1, sticky="ns")
        table_x.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.sql = tk.Text(sql_tab, wrap="word", state="disabled", font=("Menlo", 11))
        self.sql.pack(fill="both", expand=True)

    def _provider_changed(self, force_defaults: bool = False) -> None:
        provider = self.provider.get()
        if provider == "openai":
            if force_defaults or not self.model.get() or self.model.get() == "mock-test-fixtures":
                self.model.set(os.getenv("LLM_MODEL") or "gpt-5.6-sol")
            if force_defaults or not self.base_url.get():
                self.base_url.set(os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1")
        elif provider == "ollama":
            if force_defaults or not self.model.get() or self.model.get() == "mock-test-fixtures":
                self.model.set("qwen2.5-coder:7b")
            self.base_url.set("http://localhost:11434")
        else:
            self.model.set("mock-test-fixtures")
            self.base_url.set("")

    def _domain_changed(self) -> None:
        for child in self.examples_frame.winfo_children():
            child.destroy()
        ttk.Label(self.examples_frame, text="Готовые примеры:").pack(side="left")
        for example in EXAMPLES[self.domain]:
            ttk.Button(self.examples_frame, text=example, command=lambda value=example: self._set_question(value)).pack(side="left", padx=4)
        self.status.set("Проверяю базу данных…")
        threading.Thread(target=self._check_db_worker, args=(self.domain,), daemon=True).start()

    def _check_db_worker(self, domain: str) -> None:
        result = execute_readonly("SELECT 1", dsn_for_domain(domain), timeout_ms=1500, max_rows=1)
        message = "База готова" if result.success else "База недоступна — запустите Docker Desktop"
        self.root.after(0, lambda: self.status.set(message) if domain == self.domain else None)

    def _set_question(self, value: str) -> None:
        self.question.delete("1.0", "end")
        self.question.insert("1.0", value)

    def _clear(self) -> None:
        self.question.delete("1.0", "end")
        self._set_text(self.answer, "")
        self._set_text(self.sql, "")
        self._fill_table([], [])
        self.current_result = None
        self.save_button.configure(state="disabled")

    def _run(self) -> None:
        question = self.question.get("1.0", "end").strip()
        provider = self.provider.get()
        api_key = self.api_key.get().strip()
        if not question:
            messagebox.showwarning("Text2SQL", "Сначала напишите вопрос.")
            return
        if provider == "openai" and not api_key and not os.getenv("LLM_API_KEY"):
            messagebox.showwarning("Text2SQL", "Вставьте API-ключ сверху или выберите Ollama/Демо.")
            return
        values = {"question": question, "domain": self.domain, "provider": provider, "model": self.model.get().strip(), "base_url": self.base_url.get().strip(), "api_key": api_key}
        self.run_button.configure(state="disabled")
        self.progress.start(12)
        self.status.set("Составляю SQL и выполняю запрос…")
        threading.Thread(target=self._run_worker, args=(values,), daemon=True).start()

    def _run_worker(self, values: dict[str, str]) -> None:
        try:
            config = Config.from_file(None, provider=values["provider"], model=values["model"], base_url=values["base_url"], api_key_value=values["api_key"] or None)
            pipeline = Text2SQLPipeline(str(ROOT), config)
            data = run_question(pipeline, config, values["domain"], values["question"])
            self.root.after(0, lambda: self._show_result(data))
        except Exception as exc:
            self.root.after(0, lambda error=str(exc): self._show_error(error))

    def _show_result(self, data: dict) -> None:
        self.progress.stop()
        self.run_button.configure(state="normal")
        self.current_result = data
        if data["final_status"] == "success":
            self.status.set(f"Готово · {data['row_count']} строк · {data['latency_seconds']:.2f} с")
            self._set_text(self.answer, data["answer"])
            self._fill_table(data["columns"], data["rows"])
            self.save_button.configure(state="normal" if data["rows"] else "disabled")
            self.tabs.select(0)
        else:
            error = data.get("error") or "Результат не получен."
            self.status.set("Ошибка")
            self._set_text(self.answer, error)
            self._fill_table([], [])
            self.save_button.configure(state="disabled")
        details = f"SQL:\n{data['generated_sql']}\n\nСтатус: {data['execution_status']}\nМодель: {data['model']} ({data['provider']})\nВремя: {data['latency_seconds']:.4f} с\nИсправлений: {data['correction_attempts']}\n"
        if data.get("validation_errors"):
            details += "Ошибки проверки: " + "; ".join(data["validation_errors"]) + "\n"
        self._set_text(self.sql, details)

    def _show_error(self, error: str) -> None:
        self.progress.stop()
        self.run_button.configure(state="normal")
        self.status.set("Ошибка")
        self._set_text(self.answer, error)
        messagebox.showerror("Text2SQL", error)

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    def _fill_table(self, columns: list[str], rows: list[list[object]]) -> None:
        self.table.delete(*self.table.get_children())
        self.table.configure(columns=columns)
        for column in columns:
            self.table.heading(column, text=column)
            self.table.column(column, width=170, minwidth=100)
        for row in rows:
            self.table.insert("", "end", values=["" if value is None else value for value in row])

    def _save_csv(self) -> None:
        if not self.current_result:
            return
        path = filedialog.asksaveasfilename(title="Сохранить результат", defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="text2sql_result.csv")
        if not path:
            return
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(self.current_result["columns"])
            writer.writerows(self.current_result["rows"])
        messagebox.showinfo("Text2SQL", f"Файл сохранён:\n{path}")


def main() -> None:
    root = tk.Tk()
    DesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
