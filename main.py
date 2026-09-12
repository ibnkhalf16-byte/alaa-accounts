# -*- coding: utf-8 -*-
import os
import sqlite3
from datetime import datetime
import flet as ft

DB_FILE = "حسابات_علاء_ابو_شادي.db"

# =========================================================
# محرك قاعدة البيانات المعتمد
# =========================================================
class Database:
    def __init__(self, path=DB_FILE):
        self.path = path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.create_tables()

    def create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            opening_receivable REAL DEFAULT 0,
            opening_payable REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            operation TEXT NOT NULL CHECK(operation IN ('purchase','sale')),
            date TEXT NOT NULL,
            vehicle TEXT DEFAULT '',
            driver TEXT DEFAULT '',
            item TEXT NOT NULL,
            weight REAL NOT NULL DEFAULT 0,
            price REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL DEFAULT 0,
            notes TEXT DEFAULT '',
            FOREIGN KEY(person_id) REFERENCES persons(id) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            payment_type TEXT NOT NULL,
            direction TEXT NOT NULL,
            date TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            description TEXT DEFAULT '',
            FOREIGN KEY(person_id) REFERENCES persons(id) ON DELETE RESTRICT
        );
        """)
        self.conn.commit()

    def add_person(self, name, phone, address, rec, pay):
        self.conn.execute(
            "INSERT INTO persons (name, phone, address, opening_receivable, opening_payable) VALUES (?, ?, ?, ?, ?)",
            (name, phone, address, rec, pay)
        )
        self.conn.commit()

    def add_trip(self, person_id, op, date, vehicle, driver, item, weight, price):
        total = round(weight * price, 2)
        self.conn.execute(
            "INSERT INTO trips (person_id, operation, date, vehicle, driver, item, weight, price, total) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (person_id, op, date, vehicle, driver, item, weight, price, total)
        )
        self.conn.commit()

    def add_payment(self, person_id, p_type, direction, date, amount, desc):
        self.conn.execute(
            "INSERT INTO payments (person_id, payment_type, direction, date, amount, description) VALUES (?, ?, ?, ?, ?, ?)",
            (person_id, p_type, direction, date, amount, desc)
        )
        self.conn.commit()

    def get_persons(self):
        return self.conn.execute("SELECT * FROM persons ORDER BY name ASC").fetchall()

    def get_totals(self):
        sales = self.conn.execute("SELECT COALESCE(SUM(total), 0) FROM trips WHERE operation='sale'").fetchone()[0]
        purchases = self.conn.execute("SELECT COALESCE(SUM(total), 0) FROM trips WHERE operation='purchase'").fetchone()[0]
        return sales, purchases

# =========================================================
# واجهة تطبيق الموبايل (Flet)
# =========================================================
def main(page: ft.Page):
    page.title = "حسابات علاء أبو شادي"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.rtl = True
    page.padding = 10
    
    db = Database()

    def money_str(val):
        return f"{float(val or 0):,.2f} ج.م"

    # --- 1. شاشة لوحة المعلومات الرئيسية ---
    def view_dashboard():
        sales, purchases = db.get_totals()
        persons_count = len(db.get_persons())
        return ft.Column([
            ft.Text("📊 نظرة عامة", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_GREY_800),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("إجمالي المبيعات", size=14, color=ft.colors.GREY_600),
                        ft.Text(money_str(sales), size=20, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_700),
                    ]),
                    padding=15
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("إجمالي المشتريات", size=14, color=ft.colors.GREY_600),
                        ft.Text(money_str(purchases), size=20, weight=ft.FontWeight.BOLD, color=ft.colors.ORANGE_800),
                    ]),
                    padding=15
                )
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("عدد العملاء والموردين", size=14, color=ft.colors.GREY_600),
                        ft.Text(f"{persons_count} طرف", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_800),
                    ]),
                    padding=15
                )
            ),
        ], scroll=ft.ScrollMode.AUTO)

    # --- 2. شاشة تسجيل ونقلات الغلال ---
    def view_trips():
        persons = db.get_persons()
        person_dropdown = ft.Dropdown(
            label="اختر الطرف",
            options=[ft.dropdown.Option(key=str(p["id"]), text=p["name"]) for p in persons]
        )
        op_radio = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="purchase", label="شراء من مورد"),
                ft.Radio(value="sale", label="بيع لعميل"),
            ]),
            value="purchase"
        )
        item_field = ft.TextField(label="نوع البضاعة (ذرة، قمح...)", dense=True)
        weight_field = ft.TextField(label="الوزن بالطن", keyboard_type=ft.KeyboardType.NUMBER, dense=True)
        price_field = ft.TextField(label="سعر الطن", keyboard_type=ft.KeyboardType.NUMBER, dense=True)
        car_field = ft.TextField(label="رقم السيارة", dense=True)
        driver_field = ft.TextField(label="اسم السائق", dense=True)

        def save_trip(e):
            if not person_dropdown.value or not weight_field.value or not price_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("يرجى إكمال البيانات المطلوبة!"))
                page.snack_bar.open = True
                page.update()
                return
            
            db.add_trip(
                person_id=int(person_dropdown.value),
                op=op_radio.value,
                date=datetime.now().strftime("%Y-%m-%d"),
                vehicle=car_field.value,
                driver=driver_field.value,
                item=item_field.value,
                weight=float(weight_field.value),
                price=float(price_field.value)
            )
            weight_field.value = ""
            price_field.value = ""
            car_field.value = ""
            driver_field.value = ""
            page.snack_bar = ft.SnackBar(ft.Text("تم تسجيل النقلة بنجاح ✅"))
            page.snack_bar.open = True
            page.update()

        return ft.Column([
            ft.Text("🚚 تسجيل نقلة بضاعة", size=20, weight=ft.FontWeight.BOLD),
            person_dropdown,
            op_radio,
            item_field,
            ft.Row([weight_field, price_field]),
            ft.Row([car_field, driver_field]),
            ft.ElevatedButton("حفظ النقلة", on_click=save_trip, bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE, height=45),
        ], scroll=ft.ScrollMode.AUTO, spacing=12)

    # --- 3. شاشة تسجيل عميل/مورد جديد ---
    def view_persons():
        name_in = ft.TextField(label="اسم الشخص", dense=True)
        phone_in = ft.TextField(label="رقم الهاتف", keyboard_type=ft.KeyboardType.PHONE, dense=True)
        rec_in = ft.TextField(label="رصيد لك عنده (أول المدة)", value="0", keyboard_type=ft.KeyboardType.NUMBER, dense=True)
        pay_in = ft.TextField(label="رصيد له عندك (أول المدة)", value="0", keyboard_type=ft.KeyboardType.NUMBER, dense=True)

        def save_person(e):
            if not name_in.value:
                return
            db.add_person(name_in.value, phone_in.value, "", float(rec_in.value or 0), float(pay_in.value or 0))
            name_in.value = ""
            phone_in.value = ""
            page.snack_bar = ft.SnackBar(ft.Text("تم إضافة الطرف بنجاح ✅"))
            page.snack_bar.open = True
            page.update()

        return ft.Column([
            ft.Text("👥 إضافة طرف جديد", size=20, weight=ft.FontWeight.BOLD),
            name_in,
            phone_in,
            rec_in,
            pay_in,
            ft.ElevatedButton("حفظ الشخص", on_click=save_person, bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE, height=45),
        ], scroll=ft.ScrollMode.AUTO, spacing=12)

    # إدارة التنقل عبر الشريط السفلي
    body_container = ft.Container(content=view_dashboard(), expand=True)

    def nav_change(e):
        idx = e.control.selected_index
        if idx == 0:
            body_container.content = view_dashboard()
        elif idx == 1:
            body_container.content = view_trips()
        elif idx == 2:
            body_container.content = view_persons()
        page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=nav_change,
        destinations=[
            ft.NavigationDestination(icon=ft.icons.DASHBOARD_ROUNDED, label="الرئيسية"),
            ft.NavigationDestination(icon=ft.icons.LOCAL_SHIPPING_ROUNDED, label="نقلة"),
            ft.NavigationDestination(icon=ft.icons.PERSON_ADD_ROUNDED, label="إضافة عميل"),
        ]
    )

    page.add(body_container)

ft.app(target=main)

