import sqlite3
import urllib.parse
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Form Izin Keluar Kantor", page_icon="📝", layout="centered"
)


# ================= FUNGSI KONEKSI DATABASE =================
def get_db_connection():
    conn = sqlite3.connect("database_izin.db")
    conn.row_factory = sqlite3.Row
    return conn


def get_karyawan_by_nik(nik):
    conn = get_db_connection()
    user_data = conn.execute(
        "SELECT * FROM karyawan WHERE nik = ?", (nik,)
    ).fetchone()
    conn.close()
    return dict(user_data) if user_data else None


def get_all_karyawan():
    conn = get_db_connection()
    data = conn.execute("SELECT * FROM karyawan").fetchall()
    conn.close()
    return [dict(x) for x in data]


def get_all_atasan():
    conn = get_db_connection()
    data = conn.execute(
        "SELECT * FROM karyawan WHERE role = 'Atasan'"
    ).fetchall()
    conn.close()
    return [dict(x) for x in data]


def get_info_atasan(atasan_nik):
    if not atasan_nik:
        return None
    conn = get_db_connection()
    atasan = conn.execute(
        "SELECT * FROM karyawan WHERE nik = ?", (atasan_nik,)
    ).fetchone()
    conn.close()
    return dict(atasan) if atasan else None


# ================= APP HEADER & LOGIN SYSTEM =================
st.title("📱 Form Izin Keluar Kantor")

if "user_login" not in st.session_state:
    st.session_state.user_login = None

if st.session_state.user_login is None:
    st.subheader("Login Sistem")
    nik_input = st.text_input("Masukkan NIK Anda:")

    st.caption("""
    **NIK Terdaftar di Database:**
    - **IT:** Karyawan `1001` / `1002` (Atasan: `9001` - Pak Ahmad)
    - **HRD:** Karyawan `2001` (Atasan: `9002` - Bu Maya)
    """)

    if st.button("Login", type="primary"):
        data_login = get_karyawan_by_nik(nik_input)
        if data_login:
            st.session_state.user_login = data_login
            st.rerun()
        else:
            st.error("NIK tidak ditemukan di database!")

    st.stop()

# Menetapkan data login aktif
user = st.session_state.user_login

st.info(f"👤 **{user['nama']}** ({user['nik']}) — {user['dept']} [{user['role']}]")

if st.button("🚪 Logout"):
    st.session_state.user_login = None
    st.rerun()

st.divider()

# ================= TAB NAVIGASI ROLE =================
# INI BARIS KRUSIAL: Inisialisasi awal agar variabel tidak memicu NameError
tab1, tab2, tab3, tab4 = None, None, None, None

if user["role"] == "Karyawan":
    tab1, tab3 = st.tabs(["📝 Form Pengajuan", "📊 Rekap Data Saya"])
else:
    tab2, tab3, tab4 = st.tabs(
        [
            f"✅ Approval ({user['dept']})",
            "📊 Rekap Tim Saya",
            "⚙️ Kelola Karyawan & Atasan",
        ]
    )

# ----------------- TAB 1: FORM PENGAJUAN (KARYAWAN) -----------------
if tab1 is not None:
    with tab1:
        st.subheader("Pengajuan Izin Keluar")

        atasan_info = get_info_atasan(user["atasan_nik"])
        nama_atasan = atasan_info["nama"] if atasan_info else "-"

        with st.form("form_izin", clear_on_submit=True):
            st.text_input("NIK", value=user["nik"], disabled=True)
            st.text_input("Nama Karyawan", value=user["nama"], disabled=True)
            st.text_input("Departemen", value=user["dept"], disabled=True)
            st.text_input("Atasan Langsung", value=nama_atasan, disabled=True)

            alasan = st.text_area(
                "Alasan Keluar", placeholder="Urusan dinas / keluarga..."
            )
            jam_keluar = st.time_input("Rencana Jam Keluar")

            status_kembali = st.radio(
                "Status Rencana Kembali",
                ["Kembali Ke Kantor", "Tidak Kembali (Langsung Pulang)"],
            )

            jam_kembali = None
            if status_kembali == "Kembali Ke Kantor":
                jam_kembali = st.time_input("Rencana Jam Kembali")

            submitted = st.form_submit_button("Kirim Permohonan", type="primary")

            if submitted:
                if not alasan:
                    st.warning("Mohon isi alasan keluar!")
                else:
                    str_jam_kembali = (
                        jam_kembali.strftime("%H:%M")
                        if status_kembali == "Kembali Ke Kantor"
                        else "-"
                    )

                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO izin_keluar 
                        (nik, nama, dept, atasan_nik, no_wa, alasan, jam_keluar, status_kembali, jam_kembali, status, catatan)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', '-')
                    """,
                        (
                            user["nik"],
                            user["nama"],
                            user["dept"],
                            user["atasan_nik"],
                            user["no_wa"],
                            alasan,
                            jam_keluar.strftime("%H:%M"),
                            status_kembali,
                            str_jam_kembali,
                        ),
                    )
                    conn.commit()
                    last_id = cursor.lastrowid
                    conn.close()

                    st.success(
                        f"Permohonan tersimpan di sistem! (ID Pengajuan: {last_id})"
                    )

                    if atasan_info and atasan_info.get("no_wa"):
                        no_wa_atasan = atasan_info["no_wa"]
                        if no_wa_atasan.startswith("0"):
                            no_wa_atasan = "62" + no_wa_atasan[1:]

                        url_app = "http://localhost:8502"

                        pesan_wa = (
                            f"*[PERMOHONAN IZIN KELUAR KANTOR]*\n\n"
                            f"Yth. {atasan_info['nama']},\n\n"
                            f"Saya mengajukan izin keluar kantor dengan rincian:\n"
                            f"• *Nama:* {user['nama']} ({user['nik']})\n"
                            f"• *Departemen:* {user['dept']}\n"
                            f"• *Alasan:* {alasan}\n"
                            f"• *Jam Keluar:* {jam_keluar.strftime('%H:%M')}\n"
                            f"• *Rencana Kembali:* {status_kembali} ({str_jam_kembali})\n\n"
                            f"Mohon tinjau melalui link berikut:\n"
                            f"🔗 {url_app}"
                        )

                        url_wa = f"https://wa.me/{no_wa_atasan}?text={urllib.parse.quote(pesan_wa)}"

                        st.markdown(
                            f"""
                        ---
                        ### 📲 Langkah Selanjutnya:
                        <a href="{url_wa}" target="_blank">
                            <button style="
                                background-color: #25D366; 
                                color: white; 
                                border: none; 
                                padding: 12px 24px; 
                                border-radius: 8px; 
                                font-size: 16px; 
                                font-weight: bold; 
                                cursor: pointer; 
                                width: 100%;">
                                💬 Kirim Permohonan ke WhatsApp Atasan
                            </button>
                        </a>
                        """,
                            unsafe_allow_html=True,
                        )

# ----------------- TAB 2: APPROVAL (ATASAN) -----------------
if tab2 is not None:
    with tab2:
        st.subheader(f"Approval Permohonan Departemen {user['dept']}")

        conn = get_db_connection()
        pending_rows = conn.execute(
            """
            SELECT * FROM izin_keluar 
            WHERE status = 'Pending' AND atasan_nik = ?
        """,
            (user["nik"],),
        ).fetchall()
        conn.close()

        if not pending_rows:
            st.info("Tidak ada permohonan pending dari tim Anda.")
        else:
            options = {
                f"ID {row['id']} - {row['nama']}": dict(row)
                for row in pending_rows
            }
            pilihan_label = st.selectbox(
                "Pilih Permohonan Pending:", list(options.keys())
            )
            pilihan = options[pilihan_label]

            if pilihan:
                st.write("**Detail Pengajuan:**")
                st.markdown(f"""
                - **Nama Karyawan:** {pilihan['nama']} ({pilihan['nik']})
                - **Departemen:** {pilihan['dept']}
                - **Alasan:** {pilihan['alasan']}
                - **Jam Keluar:** {pilihan['jam_keluar']}
                - **Rencana Kembali:** {pilihan['status_kembali']} ({pilihan['jam_kembali']})
                """)

                catatan_atasan = st.text_input(
                    "Catatan Atasan (Opsional):", key="catatan"
                )
                col1, col2 = st.columns(2)

                def update_status(status_baru):
                    catatan = (
                        catatan_atasan if catatan_atasan else "Tidak ada catatan"
                    )

                    conn = get_db_connection()
                    conn.execute(
                        """
                        UPDATE izin_keluar 
                        SET status = ?, catatan = ? 
                        WHERE id = ?
                    """,
                        (status_baru, catatan, pilihan["id"]),
                    )
                    conn.commit()
                    conn.close()

                    no_wa = (
                        "62" + pilihan["no_wa"][1:]
                        if pilihan["no_wa"].startswith("0")
                        else pilihan["no_wa"]
                    )
                    pesan = (
                        f"*[NOTIFIKASI IZIN KELUAR KANTOR]*\n\n"
                        f"Halo {pilihan['nama']},\n"
                        f"Permohonan izin keluar Anda ({pilihan['alasan']}) "
                        f"telah *{status_baru.upper()}* oleh {user['nama']}.\n"
                        f"Catatan: {catatan}"
                    )
                    url_wa = (
                        f"https://wa.me/{no_wa}?text={urllib.parse.quote(pesan)}"
                    )

                    st.success(f"Status berhasil diubah ke: {status_baru}")
                    st.markdown(
                        f"[📱 **Klik untuk kirim Notifikasi WA ke {pilihan['nama']}**]({url_wa})"
                    )

                with col1:
                    if st.button(
                        "✅ Approve", type="primary", use_container_width=True
                    ):
                        update_status("Disetujui")
                        st.rerun()

                with col2:
                    if st.button("❌ Reject", use_container_width=True):
                        update_status("Ditolak")
                        st.rerun()

# ----------------- TAB 3: REKAP DATA -----------------
if tab3 is not None:
    with tab3:
        st.subheader("Rekap Data Permohonan Izin")

        conn = get_db_connection()
        if user["role"] == "Karyawan":
            query = "SELECT * FROM izin_keluar WHERE nik = ? ORDER BY id DESC"
            df = pd.read_sql_query(query, conn, params=(user["nik"],))
        else:
            query = "SELECT * FROM izin_keluar WHERE atasan_nik = ? ORDER BY id DESC"
            df = pd.read_sql_query(query, conn, params=(user["nik"],))
        conn.close()

        if df.empty:
            st.write("Belum ada riwayat data izin.")
        else:
            df_tampil = df[
                [
                    "id",
                    "nik",
                    "nama",
                    "dept",
                    "alasan",
                    "jam_keluar",
                    "status_kembali",
                    "jam_kembali",
                    "status",
                    "catatan",
                ]
            ]
            st.dataframe(df_tampil, use_container_width=True)

# ----------------- TAB 4: KELOLA KARYAWAN & ATASAN -----------------
if tab4 is not None:
    with tab4:
        st.subheader("⚙️ Kelola Data Karyawan & Atasan")

        sub_tab1, sub_tab2, sub_tab3 = st.tabs(
            [
                "✏️ Edit / Update Karyawan",
                "➕ Tambah Manual",
                "📁 Upload Excel Batch",
            ]
        )

        with sub_tab1:
            all_users = get_all_karyawan()
            user_dict = {f"{x['nik']} - {x['nama']}": x for x in all_users}

            selected_label = st.selectbox(
                "Pilih Karyawan yang Ingin Diubah:", list(user_dict.keys())
            )
            target_user = user_dict[selected_label]

            if target_user:
                with st.form("form_edit_user"):
                    st.write(f"**Mengubah Data NIK:** `{target_user['nik']}`")

                    new_nama = st.text_input("Nama Lengkap", value=target_user["nama"])
                    new_dept = st.text_input("Departemen", value=target_user["dept"])
                    new_wa = st.text_input("No WhatsApp", value=target_user["no_wa"])

                    new_role = st.selectbox(
                        "Role / Peran",
                        ["Karyawan", "Atasan"],
                        index=0 if target_user["role"] == "Karyawan" else 1,
                    )

                    list_atasan = get_all_atasan()
                    atasan_opts = {"- Tidak Ada -": None}
                    for a in list_atasan:
                        atasan_opts[f"{a['nik']} - {a['nama']} ({a['dept']})"] = a[
                            "nik"
                        ]

                    curr_atasan_nik = target_user["atasan_nik"]
                    default_idx = 0
                    if curr_atasan_nik:
                        for idx, (k, v) in enumerate(atasan_opts.items()):
                            if v == curr_atasan_nik:
                                default_idx = idx
                                break

                    selected_atasan_label = st.selectbox(
                        "Atasan Langsung",
                        list(atasan_opts.keys()),
                        index=default_idx,
                    )
                    new_atasan_nik = atasan_opts[selected_atasan_label]

                    submit_update = st.form_submit_button(
                        "Simpan Perubahan", type="primary"
                    )

                    if submit_update:
                        conn = get_db_connection()
                        conn.execute(
                            """
                            UPDATE karyawan 
                            SET nama = ?, dept = ?, no_wa = ?, role = ?, atasan_nik = ?
                            WHERE nik = ?
                        """,
                            (
                                new_nama,
                                new_dept,
                                new_wa,
                                new_role,
                                new_atasan_nik,
                                target_user["nik"],
                            ),
                        )

                        conn.execute(
                            """
                            UPDATE izin_keluar 
                            SET nama = ?, dept = ?, no_wa = ?, atasan_nik = ?
                            WHERE nik = ?
                        """,
                            (
                                new_nama,
                                new_dept,
                                new_wa,
                                new_atasan_nik,
                                target_user["nik"],
                            ),
                        )

                        conn.commit()
                        conn.close()

                        st.success(
                            f"Data {new_nama} ({target_user['nik']}) berhasil diperbarui!"
                        )
                        st.rerun()

        with sub_tab2:
            with st.form("form_add_user", clear_on_submit=True):
                add_nik = st.text_input("NIK Baru (Unik)")
                add_nama = st.text_input("Nama Lengkap")
                add_dept = st.text_input("Departemen")
                add_wa = st.text_input("No WhatsApp (Contoh: 08123456789)")
                add_role = st.selectbox("Role", ["Karyawan", "Atasan"])

                list_atasan = get_all_atasan()
                atasan_opts = {"- Tidak Ada -": None}
                for a in list_atasan:
                    atasan_opts[f"{a['nik']} - {a['nama']} ({a['dept']})"] = a[
                        "nik"
                    ]

                selected_atasan_label = st.selectbox(
                    "Pilih Atasan Langsung", list(atasan_opts.keys())
                )
                add_atasan_nik = atasan_opts[selected_atasan_label]

                submit_add = st.form_submit_button(
                    "Tambah Karyawan", type="primary"
                )

                if submit_add:
                    if not add_nik or not add_nama:
                        st.warning("NIK dan Nama wajib diisi!")
                    else:
                        conn = get_db_connection()
                        try:
                            conn.execute(
                                """
                                INSERT INTO karyawan (nik, nama, dept, no_wa, role, atasan_nik)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    add_nik,
                                    add_nama,
                                    add_dept,
                                    add_wa,
                                    add_role,
                                    add_atasan_nik,
                                ),
                            )
                            conn.commit()
                            st.success(
                                f"Karyawan baru {add_nama} ({add_nik}) berhasil ditambahkan!"
                            )
                        except sqlite3.IntegrityError:
                            st.error(f"NIK {add_nik} sudah terdaftar di database!")
                        finally:
                            conn.close()

        with sub_tab3:
            st.write(
                "Upload file Excel (`.xlsx`) atau CSV untuk menambah/memperbarui data massal."
            )
            st.info(
                "💡 **Format Kolom Excel Mandatory:** `nik`, `nama`, `dept`, `no_wa`, `role`, `atasan_nik`"
            )

            uploaded_file = st.file_uploader(
                "Pilih File Excel / CSV", type=["xlsx", "csv"]
            )

            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith(".csv"):
                        df_upload = pd.read_csv(uploaded_file, dtype=str)
                    else:
                        df_upload = pd.read_excel(uploaded_file, dtype=str)

                    st.write("**Pratinjau Data Upload:**")
                    st.dataframe(df_upload, use_container_width=True)

                    if st.button("🚀 Process & Import Data ke Database", type="primary"):
                        conn = get_db_connection()
                        cursor = conn.cursor()

                        count_success = 0
                        for _, row in df_upload.iterrows():
                            nik = str(row["nik"]).strip() if pd.notna(row["nik"]) else ""
                            nama = str(row["nama"]).strip() if pd.notna(row["nama"]) else ""
                            dept = str(row["dept"]).strip() if pd.notna(row["dept"]) else ""
                            no_wa = str(row["no_wa"]).strip() if pd.notna(row["no_wa"]) else ""
                            role = str(row["role"]).strip() if pd.notna(row["role"]) else "Karyawan"
                            atasan_nik = (
                                str(row["atasan_nik"]).strip()
                                if pd.notna(row["atasan_nik"]) and str(row["atasan_nik"]).strip() != ""
                                else None
                            )

                            if nik and nama:
                                cursor.execute(
                                    """
                                    INSERT INTO karyawan (nik, nama, dept, no_wa, role, atasan_nik)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                    ON CONFLICT(nik) DO UPDATE SET
                                        nama = excluded.nama,
                                        dept = excluded.dept,
                                        no_wa = excluded.no_wa,
                                        role = excluded.role,
                                        atasan_nik = excluded.atasan_nik
                                """,
                                    (nik, nama, dept, no_wa, role, atasan_nik),
                                )
                                count_success += 1

                        conn.commit()
                        conn.close()

                        st.success(
                            f"🎉 Berhasil memproses {count_success} data karyawan ke dalam database!"
                        )
                        st.rerun()

                except Exception as e:
                    st.error(f"Gagal memproses file: {e}")