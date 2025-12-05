import flet as ft
from datetime import datetime
import csv
import sqlite3

# --- VERİTABANI YÖNETİCİSİ ---
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("cepte_butce.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.tablolari_olustur()

    def tablolari_olustur(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS islemler 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, baslik TEXT, tutar REAL, tur TEXT, tarih TEXT, vade TEXT, hesap TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS varliklar 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, ad TEXT, miktar TEXT, tarih TEXT, detay TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS hedefler 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, baslik TEXT, hedef REAL, biriken REAL)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS notlar 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, baslik TEXT, icerik TEXT, tarih TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS abonelikler 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, baslik TEXT, tutar REAL, gun INTEGER, son_eklenme TEXT)''')
        self.conn.commit()

    def islem_ekle(self, baslik, tutar, tur, tarih, vade, hesap):
        self.cursor.execute("INSERT INTO islemler (baslik, tutar, tur, tarih, vade, hesap) VALUES (?, ?, ?, ?, ?, ?)", (baslik, tutar, tur, tarih, vade, hesap))
        self.conn.commit()
        return self.cursor.lastrowid

    def varlik_ekle(self, ad, miktar, tarih, detay):
        self.cursor.execute("INSERT INTO varliklar (ad, miktar, tarih, detay) VALUES (?, ?, ?, ?)", (ad, miktar, tarih, detay))
        self.conn.commit()
        return self.cursor.lastrowid

    def hedef_ekle(self, baslik, hedef, biriken):
        self.cursor.execute("INSERT INTO hedefler (baslik, hedef, biriken) VALUES (?, ?, ?)", (baslik, hedef, biriken))
        self.conn.commit()
        return self.cursor.lastrowid

    def not_ekle(self, baslik, icerik, tarih):
        self.cursor.execute("INSERT INTO notlar (baslik, icerik, tarih) VALUES (?, ?, ?)", (baslik, icerik, tarih))
        self.conn.commit()
        return self.cursor.lastrowid

    def abonelik_ekle(self, baslik, tutar, gun, son_eklenme):
        self.cursor.execute("INSERT INTO abonelikler (baslik, tutar, gun, son_eklenme) VALUES (?, ?, ?, ?)", (baslik, tutar, gun, son_eklenme))
        self.conn.commit()
        return self.cursor.lastrowid

    def sil(self, tablo, id):
        self.cursor.execute(f"DELETE FROM {tablo} WHERE id=?", (id,))
        self.conn.commit()

    def tumunu_sil(self):
        for t in ["islemler", "varliklar", "hedefler", "notlar", "abonelikler"]:
            self.cursor.execute(f"DELETE FROM {t}")
        self.conn.commit()

    def hedef_guncelle(self, id, yeni_biriken):
        self.cursor.execute("UPDATE hedefler SET biriken=? WHERE id=?", (yeni_biriken, id))
        self.conn.commit()

    def abonelik_guncelle_tarih(self, id, yeni_tarih):
        self.cursor.execute("UPDATE abonelikler SET son_eklenme=? WHERE id=?", (yeni_tarih, id))
        self.conn.commit()

    def verileri_getir(self, tablo):
        self.cursor.execute(f"SELECT * FROM {tablo}")
        data = self.cursor.fetchall()
        sonuc = []
        col_names = [description[0] for description in self.cursor.description]
        for row in data:
            sonuc.append(dict(zip(col_names, row)))
        return sonuc

db = Database()

def main(page: ft.Page):
    page.title = "Cepte Bütçe & Varlık"
    page.padding = 0 
    page.window_width = 400
    page.window_height = 800
    # DİKKAT: Scroll artık burada "AUTO" değil, duruma göre aşağıda ayarlanacak.

    # --- TEMA AYARLARI ---
    kayitli_tema = page.client_storage.get("tema_tercihi")
    page.theme_mode = ft.ThemeMode.DARK if kayitli_tema == "dark" else ft.ThemeMode.LIGHT

    def tema_degistir(e):
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        page.client_storage.set("tema_tercihi", "dark" if page.theme_mode == ft.ThemeMode.DARK else "light")
        page.update()

    def bildirim_goster(mesaj, renk="green"):
        page.snack_bar = ft.SnackBar(ft.Text(mesaj), bgcolor=renk)
        page.snack_bar.open = True
        page.update()

    # --- UYGULAMA İÇERİĞİ (Giriş Yapıldıktan Sonra Çalışır) ---
    def uygulamayi_baslat():
        page.clean() # Ekranı temizle
        
        # --- EKRAN AYARLARINI NORMALE DÖNDÜR ---
        page.scroll = "AUTO" 
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START
        page.update()

        # Verileri DB'den Çek
        islemler = db.verileri_getir("islemler")
        varliklar = db.verileri_getir("varliklar")
        hedefler = db.verileri_getir("hedefler")
        notlar = db.verileri_getir("notlar")
        abonelikler = db.verileri_getir("abonelikler")

        # --- ABONELİK KONTROL SİSTEMİ ---
        def abonelikleri_kontrol_et():
            bugun_gun = datetime.now().day
            eklenen_var_mi = False
            for ab in abonelikler:
                try:
                    son_tarih = datetime.strptime(ab.get('son_eklenme', '2000-01-01'), "%Y-%m-%d")
                    simdi = datetime.now()
                    if son_tarih.month != simdi.month and simdi.day >= int(ab['gun']):
                        yeni_id = db.islem_ekle(f"{ab['baslik']} (Otomatik)", float(ab['tutar']), "gider", simdi.strftime("%Y-%m-%d"), "Abonelik", "kisisel")
                        islemler.append({
                            "id": yeni_id, "baslik": f"{ab['baslik']} (Otomatik)", "tutar": float(ab['tutar']),
                            "tur": "gider", "tarih": simdi.strftime("%Y-%m-%d"), "vade": "Abonelik", "hesap": "kisisel"
                        })
                        yeni_tarih = simdi.strftime("%Y-%m-%d")
                        db.abonelik_guncelle_tarih(ab['id'], yeni_tarih)
                        ab['son_eklenme'] = yeni_tarih
                        eklenen_var_mi = True
                except: continue 
            if eklenen_var_mi: page.update()

        # --- GLOBAL DEĞİŞKENLER ---
        aktif_hesap = "kisisel" 

        # --- UI BİLEŞENLERİ ---
        container = ft.Container(expand=True)
        nav_bar = ft.NavigationBar(
            selected_index=0,
            destinations=[
                ft.NavigationDestination(icon=ft.Icons.HOME, label="Özet"),      
                ft.NavigationDestination(icon=ft.Icons.ADD_CIRCLE, label="Ekle"), 
                ft.NavigationDestination(icon=ft.Icons.DIAMOND, label="Varlık"), 
                ft.NavigationDestination(icon=ft.Icons.SAVINGS, label="Hedef"),
                ft.NavigationDestination(icon=ft.Icons.PIE_CHART, label="Analiz"),
            ]
        )

        def rounded_dialog(title, content, actions):
            return ft.AlertDialog(title=ft.Text(title, weight="bold"), content=content, actions=actions, shape=ft.RoundedRectangleBorder(radius=25))

        def input_style(c): 
            return ft.Container(content=c, bgcolor=ft.colors.SURFACE_VARIANT, border_radius=20, padding=10)

        def get_ozet():
            filtrelenmis = [i for i in islemler if i.get('hesap') == aktif_hesap]
            gelir = sum(i['tutar'] for i in filtrelenmis if i['tur'] == 'gelir')
            gider = sum(i['tutar'] for i in filtrelenmis if i['tur'] == 'gider')
            alacak = sum(i['tutar'] for i in filtrelenmis if i['tur'] == 'alacak')
            borc = sum(i['tutar'] for i in filtrelenmis if i['tur'] == 'borc')
            return gelir - gider, gelir, gider, alacak, borc

        # --- MENÜ FONKSİYONLARI ---
        def sifre_yonetimi_dialog(e):
            mevcut_sifre = page.client_storage.get("uygulama_sifresi")
            t_yeni = ft.TextField(label="Yeni Şifre", password=True, can_reveal_password=True)
            
            def kaydet(e):
                if t_yeni.value:
                    page.client_storage.set("uygulama_sifresi", t_yeni.value)
                    bildirim_goster("Şifre belirlendi!", "green")
                else:
                    page.client_storage.remove("uygulama_sifresi")
                    bildirim_goster("Şifre kaldırıldı!", "orange")
                dlg_pass.open = False; page.update()

            dlg_pass = rounded_dialog(
                "Güvenlik Ayarları",
                ft.Column([
                    ft.Text("Şu an şifre: " + ("VAR" if mevcut_sifre else "YOK"), color="blue"),
                    ft.Text("Şifreyi kaldırmak için boş bırakıp Kaydet'e basın.", size=12, color="grey"),
                    ft.Container(height=10), input_style(t_yeni)
                ], height=150),
                [ft.TextButton("Kapat", on_click=lambda e: setattr(dlg_pass, 'open', False) or page.update()), ft.TextButton("Kaydet", on_click=kaydet)]
            )
            page.dialog = dlg_pass; dlg_pass.open = True; page.update()

        def menuyu_ac(e):
            page.drawer = ft.NavigationDrawer(
                controls=[
                    ft.Container(height=20),
                    ft.Column([ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, size=60, color="blue"), ft.Text("Cepte Bütçe", weight="bold", size=18)], horizontal_alignment="center"),
                    ft.Divider(),
                    ft.Container(padding=ft.padding.symmetric(horizontal=20), content=ft.Row([ft.Icon(ft.Icons.DARK_MODE, color="grey"), ft.Text("Karanlık Mod", size=16, weight="bold"), ft.Switch(value=(page.theme_mode == ft.ThemeMode.DARK), on_change=tema_degistir, active_color="blue")], alignment="spaceBetween")),
                    ft.Divider(),
                    ft.NavigationDrawerDestination(icon=ft.Icons.SECURITY, label="🔐 Güvenlik / Şifre"),
                    ft.NavigationDrawerDestination(icon=ft.Icons.NOTE, label="Notlarım / Ajanda"),
                    ft.NavigationDrawerDestination(icon=ft.Icons.DOWNLOAD, label="Excel Yedekle"),
                    ft.NavigationDrawerDestination(icon=ft.Icons.DELETE_FOREVER, label="Tüm Verileri Sıfırla"),
                    ft.Divider(),
                    ft.NavigationDrawerDestination(icon=ft.Icons.EXIT_TO_APP, label="Çıkış"),
                ],
                on_change=menu_tiklama
            )
            page.drawer.open = True; page.update()

        def menu_tiklama(e):
            idx = page.drawer.selected_index
            if idx == 0: sifre_yonetimi_dialog(None)
            elif idx == 1: nav_change_manuel(5); page.drawer.open = False; page.update()
            elif idx == 2:
                try:
                    with open("cepte_butce_yedek.csv", 'w', newline='', encoding='utf-8-sig') as f:
                        w = csv.writer(f); w.writerow(["TÜR", "DETAY..."])
                        for i in islemler: w.writerow(["İşlem", i['baslik'], i['tutar']])
                    bildirim_goster("Yedeklendi: cepte_butce_yedek.csv")
                except: bildirim_goster("Hata", "red")
            elif idx == 3:
                db.tumunu_sil(); islemler.clear(); varliklar.clear(); hedefler.clear(); notlar.clear(); abonelikler.clear()
                nav_change_manuel(0); page.drawer.open = False; page.update(); bildirim_goster("Sıfırlandı", "red")
            elif idx == 4: page.window_close()

        def hesap_degistir(e):
            nonlocal aktif_hesap; aktif_hesap = list(e.control.selected)[0]
            sayfa_guncelle(nav_bar.selected_index); bildirim_goster(f"{'Ev' if aktif_hesap=='kisisel' else 'İş'} Modu", "blue")

        # --- HESAP MAKİNESİ ---
        def hesap_makinesini_ac(e):
            txt_color, bg_color, tus_bg = ft.colors.ON_SURFACE, ft.colors.SURFACE_VARIANT, ft.colors.GREY_300 if page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.GREY_800
            tema_renk = ft.colors.BLUE_600 if aktif_hesap == "kisisel" else ft.colors.ORANGE_600
            txt_result = ft.Text(value="0", color=txt_color, size=40, weight="bold", text_align="right")
            
            def btn_click(e):
                d = e.control.data
                if d == "C": txt_result.value = "0"
                elif d == "=":
                    try: txt_result.value = str(eval(txt_result.value))
                    except: txt_result.value = "Hata"
                else: txt_result.value = d if txt_result.value in ["0", "Hata"] else txt_result.value + d
                dlg_calc.update()

            def cb(t, c="white", b=tus_bg, d=None): return ft.Container(content=ft.Text(t, size=20, color=c, weight="bold"), width=60, height=60, bgcolor=b, border_radius=30, alignment=ft.alignment.center, on_click=btn_click, data=d if d else t, ink=True)

            dlg_calc = rounded_dialog("Hesap Makinesi", ft.Container(height=400, width=300, content=ft.Column([
                ft.Container(content=txt_result, padding=10, bgcolor=bg_color, border_radius=10, alignment=ft.alignment.bottom_right, height=80),
                ft.Column([ft.Row([cb("C", "white", ft.colors.RED_400), cb("/", "white", tema_renk), cb("*", "white", tema_renk), cb("-", "white", tema_renk)], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
                           ft.Row([cb("7"), cb("8"), cb("9"), cb("+", "white", tema_renk, d="+")], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
                           ft.Row([cb("4"), cb("5"), cb("6"), cb("=", "white", ft.colors.GREEN_500)], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
                           ft.Row([cb("1"), cb("2"), cb("3"), cb("0")], alignment=ft.MainAxisAlignment.SPACE_EVENLY)], spacing=10)
            ])), [ft.TextButton("Kapat", on_click=lambda e: setattr(dlg_calc, 'open', False) or page.update())])
            page.dialog = dlg_calc; dlg_calc.open = True; page.update()

        # --- 1. ANA SAYFA ---
        def home_view():
            bakiye, gelir, gider, alacak, borc = get_ozet()
            liste_konteyner = ft.Column()

            def liste_olustur(aranan=""):
                tum = [i for i in islemler if i.get('hesap') == aktif_hesap]
                if aranan: tum = [i for i in tum if aranan.lower() in i['baslik'].lower()]

                bugun_str = datetime.now().strftime("%Y-%m-%d")
                bugun_l = sorted([x for x in tum if x['tarih'] == bugun_str], key=lambda x: x['tutar'], reverse=True)
                gecmis_l = sorted([x for x in tum if x['tarih'] != bugun_str], key=lambda x: x['tarih'], reverse=True)

                def kart(x):
                    c, i, s = ("green", ft.Icons.TRENDING_UP, "+") if x['tur'] == 'gelir' else ("red", ft.Icons.TRENDING_DOWN, "-") if x['tur'] == 'gider' else ("blue", ft.Icons.ARROW_CIRCLE_DOWN, "(A)") if x['tur'] == 'alacak' else ("orange", ft.Icons.ARROW_CIRCLE_UP, "(B)")
                    d_str = datetime.strptime(x['tarih'], "%Y-%m-%d").strftime("%d.%m.%Y") if x['tarih'] else ""
                    if x.get('vade'): d_str += f" | ⏳ {x['vade']}"
                    
                    return ft.Container(padding=15, margin=ft.margin.only(bottom=10), border_radius=15, bgcolor=ft.colors.SURFACE_VARIANT, shadow=ft.BoxShadow(blur_radius=5, color=ft.colors.with_opacity(0.1, "black")), content=ft.Row([
                        ft.Container(content=ft.Icon(i, color=c), padding=10, border_radius=10, bgcolor=ft.colors.with_opacity(0.1, c)),
                        ft.Column([ft.Text(x['baslik'], weight="bold", size=16, color=ft.colors.ON_SURFACE), ft.Text(d_str, size=11, color=ft.colors.ON_SURFACE_VARIANT)], expand=True),
                        ft.Text(f"{s}{x['tutar']} TL", weight="bold", color=c, size=16),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ft.colors.ON_SURFACE_VARIANT, on_click=lambda e, xx=x: sil_islem_ve_yenile(xx))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

                widget_bugun = [kart(x) for x in bugun_l] or [ft.Container(content=ft.Text("Bugün işlem yok.", color=ft.colors.ON_SURFACE_VARIANT), alignment=ft.alignment.center, padding=10)]
                
                return [
                    ft.Row([ft.Text("BUGÜN", size=14, weight="bold", color=ft.colors.ON_SURFACE_VARIANT), ft.Icon(ft.Icons.TODAY, size=16, color=ft.colors.ON_SURFACE_VARIANT)]),
                    ft.Container(height=10), ft.Column(widget_bugun, spacing=0),
                    ft.Container(height=10), ft.Divider(),
                    ft.ExpansionTile(title=ft.Text("Geçmiş İşlemler", size=14, weight="bold", color=ft.colors.ON_SURFACE_VARIANT), leading=ft.Icon(ft.Icons.HISTORY, color=ft.colors.ON_SURFACE_VARIANT), collapsed_text_color=ft.colors.ON_SURFACE_VARIANT, text_color=ft.colors.ON_SURFACE, controls=[ft.Container(height=10), ft.Column([kart(x) for x in gecmis_l] if gecmis_l else [ft.Text("Geçmiş yok.", color=ft.colors.ON_SURFACE_VARIANT)])], initially_expanded=(aranan != ""))
                ]

            def sil_islem_ve_yenile(x):
                db.sil("islemler", x['id'])
                islemler.remove(x)
                liste_konteyner.controls = liste_olustur()
                liste_konteyner.update()
                page.snack_bar = ft.SnackBar(ft.Text("İşlem silindi"), bgcolor="red"); page.snack_bar.open = True; page.update()
                nav_change_manuel(0)

            liste_konteyner.controls = liste_olustur()
            tema_renk, tema_acik = (ft.colors.BLUE_700, ft.colors.BLUE_800) if aktif_hesap == "kisisel" else (ft.colors.ORANGE_700, ft.colors.ORANGE_800)
            
            return ft.Container(content=ft.Column([
                ft.Container(padding=20, border_radius=ft.border_radius.only(bottom_left=30, bottom_right=30), bgcolor=tema_renk, content=ft.Column([
                    ft.Row([ft.IconButton(ft.Icons.MENU, icon_color="white", on_click=menuyu_ac), ft.SegmentedButton(selected={aktif_hesap}, on_change=hesap_degistir, allow_multiple_selection=False, allow_empty_selection=False, style=ft.ButtonStyle(color={ft.MaterialState.SELECTED: "black", ft.MaterialState.DEFAULT: "white"}, bgcolor={ft.MaterialState.SELECTED: "white", ft.MaterialState.DEFAULT: "transparent"}), segments=[ft.Segment(value="kisisel", label=ft.Text("🏠"), icon=ft.Icon(ft.Icons.HOME)), ft.Segment(value="is", label=ft.Text("🏪"), icon=ft.Icon(ft.Icons.STORE))]), ft.IconButton(ft.Icons.CALCULATE, icon_color="white", on_click=hesap_makinesini_ac)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(height=15), ft.Text("Nakit Durumu (Bakiye)", color="white70", size=12), ft.Text(f"{bakiye} TL", size=40, weight="bold", color="white"), ft.Container(height=20),
                    ft.Container(bgcolor=tema_acik, padding=15, border_radius=15, content=ft.Column([ft.Row([ft.Column([ft.Text("Gelir", color="white70", size=12), ft.Text(f"+{gelir}", color="white", weight="bold")]), ft.Container(width=1, height=30, bgcolor="white24"), ft.Column([ft.Text("Gider", color="white70", size=12), ft.Text(f"-{gider}", color="white", weight="bold")])], alignment=ft.MainAxisAlignment.SPACE_EVENLY), ft.Divider(color="white24", thickness=0.5), ft.Row([ft.Column([ft.Text("Alacak", color="white70", size=12), ft.Text(f"{alacak}", color="white", weight="bold")]), ft.Container(width=1, height=30, bgcolor="white24"), ft.Column([ft.Text("Borç", color="white70", size=12), ft.Text(f"{borc}", color="white", weight="bold")])], alignment=ft.MainAxisAlignment.SPACE_EVENLY)]))
                ])),
                ft.Container(padding=ft.padding.symmetric(horizontal=20), content=ft.TextField(prefix_icon=ft.Icons.SEARCH, hint_text="İşlem Ara...", border_radius=15, bgcolor=ft.colors.SURFACE_VARIANT, border_color="transparent", text_size=14, on_change=lambda e: (setattr(liste_konteyner, 'controls', liste_olustur(e.control.value)) or liste_konteyner.update()))),
                ft.Container(padding=20, content=liste_konteyner)
            ], scroll=ft.ScrollMode.AUTO))

        # 2. EKLEME SAYFASI
        def add_view():
            ibg, icol = ft.colors.SURFACE_VARIANT, ft.colors.ON_SURFACE
            txt_desc = ft.TextField(label="Açıklama", hint_text="Örn: Market", border_color="transparent", bgcolor=ibg, color=icol)
            txt_amount = ft.TextField(label="Tutar", suffix_text="TL", keyboard_type=ft.KeyboardType.NUMBER, border_color="transparent", bgcolor=ibg, color=icol)
            
            def tarih_formatla(e):
                v = ''.join(filter(str.isdigit, e.control.value)); e.control.value = (v[:2] + "." + v[2:] if len(v) > 2 else v) if len(v) <= 4 else (v[:2] + "." + v[2:4] + "." + v[4:] if len(v) > 4 else v); e.control.update()

            txt_vade = ft.TextField(label="Tarih (GG.AA.YYYY)", hint_text="Boşsa Bugün", keyboard_type=ft.KeyboardType.NUMBER, border_color="transparent", bgcolor=ibg, color=icol, on_change=tarih_formatla, max_length=10)
            radio_tur = ft.RadioGroup(content=ft.Row([ft.Radio(value="gider", label="Gider"), ft.Radio(value="gelir", label="Gelir"), ft.Radio(value="alacak", label="Alacak"), ft.Radio(value="borc", label="Borç")]), value="gider")

            def kaydet_tikla(e):
                if not txt_desc.value or not txt_amount.value: bildirim_goster("Eksik bilgi!", "red"); return
                kayit_tarihi = datetime.now().strftime("%Y-%m-%d")
                if txt_vade.value:
                    try: kayit_tarihi = datetime.strptime(txt_vade.value, "%d.%m.%Y").strftime("%Y-%m-%d")
                    except: bildirim_goster("Tarih Hatalı!", "red"); return
                try:
                    tutar_val = float(txt_amount.value.replace(",", "."))
                    y_id = db.islem_ekle(txt_desc.value, tutar_val, radio_tur.value, kayit_tarihi, txt_vade.value, aktif_hesap)
                    islemler.append({"id": y_id, "baslik": txt_desc.value, "tutar": tutar_val, "tur": radio_tur.value, "tarih": kayit_tarihi, "vade": txt_vade.value, "hesap": aktif_hesap})
                    bildirim_goster("Kaydedildi!"); nav_change_manuel(0)
                except Exception as ex: bildirim_goster(f"Hata: {str(ex)}", "red")

            # ABONELİK EKLEME
            def abonelik_ekle_dialog(e):
                a_baslik = ft.TextField(label="Abonelik Adı", hint_text="Netflix, Kira...")
                a_tutar = ft.TextField(label="Aylık Tutar", keyboard_type="number")
                a_gun = ft.TextField(label="Her Ayın Hangi Günü?", hint_text="1-31 arası", keyboard_type="number")
                
                def save(e):
                    try:
                        g = int(a_gun.value); t = float(a_tutar.value)
                        if not (1 <= g <= 31): raise ValueError
                        y_id = db.abonelik_ekle(a_baslik.value, t, g, "2000-01-01")
                        abonelikler.append({"id": y_id, "baslik": a_baslik.value, "tutar": t, "gun": g, "son_eklenme": "2000-01-01"})
                        page.dialog.open = False; page.update(); bildirim_goster("Abonelik Takibi Başlatıldı!", "orange")
                    except: bildirim_goster("Bilgileri kontrol edin", "red")
                
                page.dialog = rounded_dialog("Abonelik Ekle", ft.Column([a_baslik, a_tutar, a_gun], height=200), [ft.TextButton("Kaydet", on_click=save)])
                page.dialog.open = True; page.update()

            # ABONELİK YÖNETİM
            def abonelikleri_yonet_dialog(e):
                def sil_abonelik(ab):
                    db.sil("abonelikler", ab['id']); abonelikler.remove(ab); liste_guncelle(); page.update(); bildirim_goster("Abonelik silindi", "red")
                
                liste_col = ft.Column(scroll=ft.ScrollMode.AUTO)
                def liste_guncelle():
                    items = []
                    if not abonelikler: items.append(ft.Text("Kayıtlı abonelik yok.", color="grey"))
                    else:
                        for ab in abonelikler:
                            items.append(ft.Container(padding=15, bgcolor=ft.colors.SURFACE_VARIANT, border_radius=20, content=ft.Row([ft.Column([ft.Text(ab['baslik'], weight="bold", size=16), ft.Text(f"{ab['tutar']} TL - Her ayın {ab['gun']}. günü", size=12, color="grey")]), ft.IconButton(ft.Icons.DELETE, icon_color="red", on_click=lambda e, x=ab: sil_abonelik(x))], alignment="spaceBetween")))
                    liste_col.controls = items
                liste_guncelle()
                page.dialog = rounded_dialog("Aboneliklerim", ft.Container(content=liste_col, height=300, width=300), [ft.TextButton("Kapat", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update())])
                page.dialog.open = True; page.update()

            return ft.Container(padding=20, content=ft.Column([
                ft.Text("Yeni İşlem", size=24, weight="bold", color=ft.colors.ON_SURFACE), ft.Container(padding=10, border_radius=10, bgcolor=ft.colors.BLUE_50 if aktif_hesap == "kisisel" else ft.colors.ORANGE_50, content=ft.Row([ft.Icon(ft.Icons.INFO, color="blue" if aktif_hesap == "kisisel" else "orange"), ft.Text(f"Bu işlem '{'EV' if aktif_hesap == 'kisisel' else 'İŞ YERİ'}' hesabına eklenecek.", color="black", weight="bold")])), ft.Container(height=20),
                input_style(txt_desc), ft.Container(height=15), input_style(txt_amount), ft.Container(height=15), input_style(txt_vade),
                ft.Container(height=15), ft.Container(content=radio_tur, bgcolor=ibg, padding=10, border_radius=15),
                ft.Container(height=25), ft.ElevatedButton("KAYDET", on_click=kaydet_tikla, bgcolor=ft.colors.BLUE_600 if aktif_hesap=="kisisel" else ft.colors.ORANGE_600, color="white", width=400, height=50),
                ft.Container(height=10),
                ft.Row([ft.OutlinedButton("ABONELİK EKLE", on_click=abonelik_ekle_dialog, style=ft.ButtonStyle(color="orange"), expand=True), ft.Container(width=10), ft.OutlinedButton("YÖNET", on_click=abonelikleri_yonet_dialog, style=ft.ButtonStyle(color="blue"), expand=True)])
            ], scroll=ft.ScrollMode.AUTO))

        # --- 3. VARLIKLAR SAYFASI ---
        def assets_view():
            ibg, icol = ft.colors.SURFACE_VARIANT, ft.colors.ON_SURFACE
            dd_ad = ft.Dropdown(label="Varlık Seç", hint_text="Listeden seçin...", border_color="purple", options=[ft.dropdown.Option(x) for x in ["Dolar (USD)", "Euro (EUR)", "Gram Altın", "Çeyrek Altın", "Cumhuriyet Altını", "Bitcoin (BTC)", "Ethereum (ETH)", "Hisse Senedi (BIST)", "Nakit (TL Kasa)"]], bgcolor=ibg, color=icol)
            txt_miktar = ft.TextField(label="Miktar", hint_text="Adet / Tutar", keyboard_type=ft.KeyboardType.NUMBER, border_color="purple", bgcolor=ibg, color=icol)
            txt_detay = ft.TextField(label="Hisse Adı / Açıklama", hint_text="Örn: THYAO, Maaş Artışı", border_color="purple", bgcolor=ibg, color=icol)
            
            def vk(e):
                if not dd_ad.value or not txt_miktar.value: return
                dt = datetime.now().strftime("%Y-%m-%d"); dty = txt_detay.value if txt_detay.value else ""
                y_id = db.varlik_ekle(dd_ad.value, txt_miktar.value, dt, dty)
                varliklar.append({"id": y_id, "ad": dd_ad.value, "miktar": txt_miktar.value, "detay": dty, "tarih": dt})
                dlg_modal.open = False; page.update(); nav_change_manuel(2)

            dlg_modal = rounded_dialog("Varlık Ekle", ft.Column([input_style(dd_ad), ft.Container(height=15), input_style(txt_miktar), ft.Container(height=15), input_style(txt_detay)], height=250), [ft.TextButton("İptal", on_click=lambda e: setattr(dlg_modal, 'open', False) or page.update()), ft.TextButton("Kaydet", on_click=vk)])
            
            def vs(x): db.sil("varliklar", x['id']); varliklar.remove(x); nav_change_manuel(2)

            gr = {}; ac = []
            for v in varliklar: 
                if v['ad'] not in gr: gr[v['ad']] = []
                gr[v['ad']].append(v)
            
            if not varliklar: ac.append(ft.Container(content=ft.Text("Henüz varlık eklemediniz.", color=ft.colors.ON_SURFACE_VARIANT), alignment=ft.alignment.center, padding=20))
            
            for ad, l in gr.items():
                tm = 0.0; tg = f"{len(l)} Kalem"
                try: tm = sum(float(x['miktar'].replace(",", ".")) for x in l); tg = f"{tm:g}"
                except: pass
                al = ad.lower(); ic, co = (ft.Icons.CURRENCY_EXCHANGE, "green") if any(x in al for x in ["dolar","euro","tl"]) else (ft.Icons.MONETIZATION_ON, "orange") if "altın" in al else (ft.Icons.CURRENCY_BITCOIN, "purple") if any(x in al for x in ["coin","btc"]) else (ft.Icons.CANDLESTICK_CHART, "blue") if "hisse" in al else (ft.Icons.DIAMOND, "cyan")
                ds = []
                for v in l:
                    ts = v.get('tarih', '-'); detay = v.get('detay', '')
                    ds.append(ft.Container(padding=10, bgcolor=ft.colors.SURFACE, border_radius=10, margin=ft.margin.only(bottom=5), content=ft.Row([ft.Row([ft.Icon(ft.Icons.HISTORY, size=16, color=ft.colors.ON_SURFACE_VARIANT), ft.Column([ft.Text(f"{ts}", color=ft.colors.ON_SURFACE_VARIANT, size=10), ft.Text(f"{detay}", color=ft.colors.PRIMARY, size=12, weight="bold") if detay else ft.Container()], spacing=2)]), ft.Text(f"{v['miktar']}", weight="bold", color=ft.colors.ON_SURFACE), ft.IconButton(ft.Icons.DELETE, icon_color="red", icon_size=18, on_click=lambda e, x=v: vs(x))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)))
                ac.append(ft.Card(elevation=2, content=ft.ExpansionTile(leading=ft.Icon(ic, color=co, size=30), title=ft.Text(ad, weight="bold", size=16, color=ft.colors.ON_SURFACE), subtitle=ft.Text(f"Toplam: {tg}", color=ft.colors.ON_SURFACE_VARIANT, weight="bold"), bgcolor=ft.colors.SURFACE_VARIANT, controls=[ft.Container(padding=15, content=ft.Column(ds))])))

            return ft.Container(content=ft.Column([
                ft.Container(padding=20, border_radius=ft.border_radius.only(bottom_left=30, bottom_right=30), gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=[ft.colors.PURPLE_700, ft.colors.DEEP_PURPLE_900]), content=ft.Row([ft.Icon(ft.Icons.DIAMOND, color="white", size=30), ft.Column([ft.Text("VARLIKLARIM", color="white", size=20, weight="bold"), ft.Text("Kasa, Altın, Döviz Listesi", color="white70", size=12)], alignment=ft.MainAxisAlignment.CENTER), ft.Container(width=30)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)),
                ft.Container(padding=20, content=ft.Column([ft.Row([ft.Text("LİSTE", size=14, weight="bold", color=ft.colors.ON_SURFACE_VARIANT), ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="purple", tooltip="Ekle", on_click=lambda e: page.open(dlg_modal))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(height=10), ft.Column(ac)]))
            ], scroll=ft.ScrollMode.AUTO))

        # --- 4. HEDEFLER SAYFASI ---
        def goals_view():
            ibg, icol = ft.colors.SURFACE_VARIANT, ft.colors.ON_SURFACE
            t_baslik = ft.TextField(label="Hedef Adı", hint_text="Örn: Araba", border_color="orange", bgcolor=ibg, color=icol)
            t_hedef = ft.TextField(label="Hedeflenen Tutar", hint_text="800000", keyboard_type=ft.KeyboardType.NUMBER, border_color="orange", bgcolor=ibg, color=icol)
            t_biriken = ft.TextField(label="Başlangıç Birikimi", hint_text="0", keyboard_type=ft.KeyboardType.NUMBER, border_color="orange", value="0", bgcolor=ibg, color=icol)
            
            def hedef_kaydet(e):
                if not t_baslik.value or not t_hedef.value: return
                try:
                    hd = float(t_hedef.value.replace(",", ".")); br = float(t_biriken.value.replace(",", "."))
                    y_id = db.hedef_ekle(t_baslik.value, hd, br)
                    hedefler.append({"id": y_id, "baslik": t_baslik.value, "hedef": hd, "biriken": br})
                    dlg_add.open = False; page.update(); nav_change_manuel(3)
                except: bildirim_goster("Sayısal değer girin", "red")

            dlg_add = rounded_dialog("Yeni Hedef", ft.Column([input_style(t_baslik), ft.Container(height=10), input_style(t_hedef), ft.Container(height=10), input_style(t_biriken)], height=250), [ft.TextButton("İptal", on_click=lambda e: setattr(dlg_add, 'open', False) or page.update()), ft.TextButton("Kaydet", on_click=hedef_kaydet)])

            def hedef_guncelle_dialog(hedef_item):
                t_yeni_biriken = ft.TextField(label="Güncel Biriken Tutar", value=str(hedef_item['biriken']), keyboard_type=ft.KeyboardType.NUMBER, border_color="green", bgcolor=ibg, color=icol)
                def kaydet(e):
                    try:
                        yeni_val = float(t_yeni_biriken.value.replace(",", "."))
                        db.hedef_guncelle(hedef_item['id'], yeni_val)
                        hedef_item['biriken'] = yeni_val
                        dlg_update.open = False; page.update(); nav_change_manuel(3)
                    except: bildirim_goster("Hata", "red")
                dlg_update = rounded_dialog(f"{hedef_item['baslik']} Güncelle", input_style(t_yeni_biriken), [ft.TextButton("İptal", on_click=lambda e: setattr(dlg_update, 'open', False) or page.update()), ft.TextButton("Güncelle", on_click=kaydet)])
                page.open(dlg_update)

            def hedef_sil(x): db.sil("hedefler", x['id']); hedefler.remove(x); nav_change_manuel(3)

            cards = []
            if not hedefler: cards.append(ft.Container(content=ft.Text("Henüz hedef yok.", color=ft.colors.ON_SURFACE_VARIANT), alignment=ft.alignment.center, padding=20))

            for h in hedefler:
                yuzde = h['biriken'] / h['hedef'] if h['hedef'] > 0 else 0
                renk = "green" if yuzde >= 1 else "orange"
                cards.append(ft.Card(elevation=4, content=ft.Container(padding=15, bgcolor=ft.colors.SURFACE_VARIANT, content=ft.Column([
                    ft.Row([ft.Text(h['baslik'], size=18, weight="bold", color=ft.colors.ON_SURFACE), ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red", icon_size=20, on_click=lambda e, x=h: hedef_sil(x))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.ProgressBar(value=min(yuzde, 1.0), color=renk, bgcolor=ft.colors.with_opacity(0.2, "grey"), height=10),
                    ft.Container(height=5),
                    ft.Row([ft.Text(f"{h['biriken']:,.0f} / {h['hedef']:,.0f} TL".replace(",", "."), size=12, color=ft.colors.ON_SURFACE_VARIANT), ft.Text(f"%{int(yuzde*100)}", weight="bold", color=renk)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(height=10),
                    ft.OutlinedButton("Para Ekle / Düzenle", icon=ft.Icons.EDIT, on_click=lambda e, x=h: hedef_guncelle_dialog(x), style=ft.ButtonStyle(color=ft.colors.PRIMARY))
                ])), margin=ft.margin.only(bottom=10)))

            return ft.Container(content=ft.Column([
                ft.Container(padding=20, border_radius=ft.border_radius.only(bottom_left=30, bottom_right=30), gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=[ft.colors.TEAL_700, ft.colors.TEAL_900]), content=ft.Row([ft.Icon(ft.Icons.SAVINGS, color="white", size=30), ft.Column([ft.Text("HEDEF KUMBARAM", color="white", size=20, weight="bold"), ft.Text("Hayallerine Ulaş", color="white70", size=12)], alignment=ft.MainAxisAlignment.CENTER), ft.Container(width=30)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)),
                ft.Container(padding=20, content=ft.Column([ft.Row([ft.Text("HEDEFLERİM", size=14, weight="bold", color=ft.colors.ON_SURFACE_VARIANT), ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="teal", tooltip="Yeni Hedef", on_click=lambda e: page.open(dlg_add))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(height=10), ft.Column(cards)]))
            ], scroll=ft.ScrollMode.AUTO))

        # --- 5. NOTLAR SAYFASI ---
        def notes_view():
            ibg, icol = ft.colors.TRANSPARENT, ft.colors.ON_SURFACE
            t_baslik = ft.TextField(label="Başlık", hint_text="Örn: Fatura", border_color="indigo", bgcolor=ibg, color=icol)
            t_not = ft.TextField(label="İçerik", hint_text="Detaylar...", multiline=True, min_lines=3, border_color="indigo", bgcolor=ibg, color=icol)
            
            def not_kaydet(e):
                if not t_baslik.value and not t_not.value: return
                ts = datetime.now().strftime("%d.%m.%Y %H:%M"); bs = t_baslik.value if t_baslik.value else "Başlıksız"
                y_id = db.not_ekle(bs, t_not.value, ts)
                notlar.append({"id": y_id, "baslik": bs, "icerik": t_not.value, "tarih": ts})
                dlg_add.open = False; page.update(); nav_change_manuel(5)

            dlg_add = rounded_dialog("Not Ekle", ft.Column([input_style(t_baslik), ft.Container(height=10), input_style(t_not)], height=250), [ft.TextButton("İptal", on_click=lambda e: setattr(dlg_add, 'open', False) or page.update()), ft.TextButton("Kaydet", on_click=not_kaydet)])
            
            def ns(x): db.sil("notlar", x['id']); notlar.remove(x); nav_change_manuel(5)

            cards = []
            if not notlar: cards.append(ft.Container(content=ft.Text("Henüz not yok.", color=ft.colors.ON_SURFACE_VARIANT), alignment=ft.alignment.center, padding=20))
            for n in reversed(notlar):
                baslik = n.get('baslik', 'Başlıksız')
                cards.append(ft.Card(elevation=2, content=ft.Container(padding=15, bgcolor=ft.colors.SURFACE_VARIANT, content=ft.Column([
                    ft.Row([ft.Column([ft.Text(baslik, size=18, weight="bold", color=ft.colors.ON_SURFACE), ft.Text(n['tarih'], size=12, color="grey")]), ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red", icon_size=20, on_click=lambda e, x=n: ns(x))], alignment="spaceBetween"),
                    ft.Divider(height=10, color="grey"), ft.Text(n['icerik'], size=15, color=ft.colors.ON_SURFACE)
                ])), margin=ft.margin.only(bottom=10)))

            return ft.Container(content=ft.Column([
                ft.Container(padding=20, border_radius=ft.border_radius.only(bottom_left=30, bottom_right=30), gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=[ft.colors.INDIGO_700, ft.colors.INDIGO_900]), content=ft.Row([ft.Icon(ft.Icons.NOTE_ALT, color="white", size=30), ft.Column([ft.Text("AJANDA & NOTLAR", color="white", size=20, weight="bold"), ft.Text("Unutmamak İçin Not Al", color="white70", size=12)], alignment=ft.MainAxisAlignment.CENTER), ft.Container(width=30)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)),
                ft.Container(padding=20, content=ft.Column([ft.Row([ft.Text("NOTLARIM", size=14, weight="bold", color=ft.colors.ON_SURFACE_VARIANT), ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="indigo", tooltip="Yeni Not", on_click=lambda e: page.open(dlg_add))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(height=10), ft.Column(cards)]))
            ], scroll=ft.ScrollMode.AUTO))

        # 6. Analiz Sayfası
        def stats_view():
            tc = ft.colors.ON_SURFACE
            center_text = ft.Text("0 TL", size=20, weight=ft.FontWeight.BOLD, color=tc)
            chart = ft.PieChart(sections=[], center_space_radius=60, height=250)
            ozet_listesi = ft.Column()

            def verileri_hazirla(periyot):
                bugun = datetime.now()
                hesap_islemleri = [i for i in islemler if i.get('hesap') == aktif_hesap]
                filtrelenmis = []
                
                for i in hesap_islemleri:
                    try:
                        t = datetime.strptime(i['tarih'], "%Y-%m-%d")
                        if periyot == "Günlük" and t.date() == bugun.date(): filtrelenmis.append(i)
                        elif periyot == "Aylık" and t.month == bugun.month and t.year == bugun.year: filtrelenmis.append(i)
                        elif periyot == "Yıllık" and t.year == bugun.year: filtrelenmis.append(i)
                    except: continue
                
                tg = sum(x['tutar'] for x in filtrelenmis if x['tur'] == 'gelir')
                td = sum(x['tutar'] for x in filtrelenmis if x['tur'] == 'gider')
                ta = sum(x['tutar'] for x in filtrelenmis if x['tur'] == 'alacak')
                tb = sum(x['tutar'] for x in filtrelenmis if x['tur'] == 'borc')
                toplam = tg + td + ta + tb
                
                sect = []
                if toplam == 0:
                    sect.append(ft.PieChartSection(value=1, color="grey", radius=20, title=""))
                    center_text.value = "Veri Yok"; center_text.color = ft.colors.ON_SURFACE_VARIANT
                else:
                    if tg > 0: sect.append(ft.PieChartSection(value=tg, color="green", radius=50, title=f"%{int(tg/toplam*100)}", title_style=ft.TextStyle(color="white", weight="bold")))
                    if td > 0: sect.append(ft.PieChartSection(value=td, color="red", radius=50, title=f"%{int(td/toplam*100)}", title_style=ft.TextStyle(color="white", weight="bold")))
                    if ta > 0: sect.append(ft.PieChartSection(value=ta, color="blue", radius=50, title=f"%{int(ta/toplam*100)}", title_style=ft.TextStyle(color="white", weight="bold")))
                    if tb > 0: sect.append(ft.PieChartSection(value=tb, color="orange", radius=50, title=f"%{int(tb/toplam*100)}", title_style=ft.TextStyle(color="white", weight="bold")))
                    net = tg - td
                    center_text.value = f"{net} TL"; center_text.color = "green" if net >= 0 else "red"
                
                chart.sections = sect
                def satir(ikon, renk, baslik, tutar): return ft.ListTile(leading=ft.Icon(ikon, color=renk), title=ft.Text(baslik, color=tc), trailing=ft.Text(f"{tutar} TL", weight="bold", color=tc))
                ozet_listesi.controls = [satir(ft.Icons.TRENDING_UP, "green", "Gelir", tg), satir(ft.Icons.TRENDING_DOWN, "red", "Gider", td), satir(ft.Icons.ARROW_CIRCLE_DOWN, "blue", "Alacak (Veresiye)", ta), satir(ft.Icons.ARROW_CIRCLE_UP, "orange", "Borç", tb)]
                page.update()

            def tab_degisti(e): verileri_hazirla(["Günlük", "Aylık", "Yıllık"][e.control.selected_index])
            verileri_hazirla("Aylık")

            return ft.Container(padding=20, content=ft.Column([
                ft.Text(f"Analiz: {'Kişisel' if aktif_hesap == 'kisisel' else 'İş Yeri'}", size=24, weight="bold", color=tc), 
                ft.Container(height=10),
                ft.Tabs(selected_index=1, on_change=tab_degisti, tabs=[ft.Tab(text="Günlük"), ft.Tab(text="Aylık"), ft.Tab(text="Yıllık")]),
                ft.Container(height=20), ft.Stack([chart, ft.Container(alignment=ft.alignment.center, content=center_text)], height=250), ft.Container(height=20), ozet_listesi
            ], scroll=ft.ScrollMode.AUTO))

        def nav_change_manuel(index):
            if index < 6: nav_bar.selected_index = index; sayfa_guncelle(index)

        def sayfa_guncelle(index):
            container.content = None
            if index == 0: container.content = home_view()
            elif index == 1: container.content = add_view()
            elif index == 2: container.content = assets_view()
            elif index == 3: container.content = goals_view()
            elif index == 4: container.content = stats_view()
            elif index == 5: container.content = notes_view()
            page.update()

        nav_bar.on_change = lambda e: sayfa_guncelle(e.control.selected_index)
        page.add(container, nav_bar)
        abonelikleri_kontrol_et()
        nav_change_manuel(0)

    # --- AÇILIŞ KONTROLÜ (ŞİFRE VAR MI?) ---
    kayitli_sifre = page.client_storage.get("uygulama_sifresi")

    if kayitli_sifre:
        # ŞİFRE EKRANI AYARLARI (Kaydırma kapalı, tam ortala)
        page.scroll = None
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        sifre_input = ft.TextField(label="Şifreniz", password=True, text_align="center", width=200)
        def giris_yap(e):
            if sifre_input.value == kayitli_sifre:
                uygulamayi_baslat()
            else:
                bildirim_goster("Hatalı Şifre!", "red")

        page.add(
            ft.Column([
                ft.Icon(ft.Icons.LOCK, size=80, color="blue"),
                ft.Text("Hoşgeldiniz", size=24, weight="bold"),
                ft.Container(height=10),
                sifre_input,
                ft.Container(height=10),
                ft.ElevatedButton("GİRİŞ YAP", on_click=giris_yap, bgcolor="blue", color="white", width=200)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
    else:
        # Şifre yoksa direkt başlat
        uygulamayi_baslat()

ft.app(target=main)