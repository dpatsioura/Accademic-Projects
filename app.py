import streamlit as st
import pandas as pd
import sqlite3
import os
import re
import zipfile
from datetime import date, datetime
from io import BytesIO

st.set_page_config(page_title="Academic Projects", layout="wide")

def create_safe_folder_name(name):
    clean_name = re.sub(r'[^a-zA-Z0-9\u0370-\u03FF ]', '_', name.strip())
    return clean_name.replace(' ', '_')

def save_uploaded_file(uploadedfile, folder_name):
    if uploadedfile is not None and folder_name:
        safe_folder = create_safe_folder_name(folder_name)
        base_path = os.path.join("uploads", "Projects", safe_folder)
        
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            
        file_path = os.path.join(base_path, uploadedfile.name)
        with open(file_path, "wb") as f:
            f.write(uploadedfile.getbuffer())
        return file_path
    return ""

conn = sqlite3.connect('projects_app_v1.db', check_same_thread=False)

conn.execute('''CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT, proposal_deadline TEXT, date_from TEXT, date_to TEXT, total_funding REAL)''')
conn.execute('''CREATE TABLE IF NOT EXISTS stakeholders (id INTEGER PRIMARY KEY, project_name TEXT, name TEXT, funding REAL, role TEXT)''')
conn.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, project_name TEXT, stakeholder_name TEXT, quarter TEXT, description TEXT, deadline TEXT)''')
conn.commit()

st.title("Academic Projects")

with st.expander("Δημιουργία Νέου Έργου ή Πρότασης"):
    with st.form("new_project_form", clear_on_submit=True):
        new_project = st.text_input("Όνομα Έργου / Ακρωνύμιο")
        new_funding = st.number_input("Συνολική Χρηματοδότηση σε Ευρώ", min_value=0.0, format="%.2f")
        
        st.write("Χρονοδιάγραμμα")
        new_deadline = st.date_input("Deadline Υποβολής Πρότασης", format="DD/MM/YYYY")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            new_proj_from = st.date_input("Έναρξη Έργου", format="DD/MM/YYYY")
        with col_p2:
            new_proj_to = st.date_input("Λήξη Έργου", format="DD/MM/YYYY")
        
        submitted_proj = st.form_submit_button("Δημιουργία Φακέλου Έργου")
        if submitted_proj:
            if new_project:
                conn.execute('INSERT INTO projects (name, proposal_deadline, date_from, date_to, total_funding) VALUES (?, ?, ?, ?, ?)', 
                           (new_project, new_deadline.strftime('%d/%m/%Y'), new_proj_from.strftime('%d/%m/%Y'), new_proj_to.strftime('%d/%m/%Y'), new_funding))
                conn.commit()
                os.makedirs(os.path.join("uploads", "Projects", create_safe_folder_name(new_project)), exist_ok=True)
                st.success("Το έργο δημιουργήθηκε")
                st.rerun()
            else:
                st.error("Γράψε ένα όνομα για το έργο")

projects_df = pd.read_sql_query('SELECT * FROM projects', conn)
if not projects_df.empty:
    project_names = projects_df['name'].tolist()
    selected_project = st.selectbox("Άνοιγμα Φακέλου Έργου", ["Επίλεξε..."] + project_names)
    
    if selected_project != "Επίλεξε...":
        proj_info = projects_df[projects_df['name'] == selected_project].iloc[0]
        st.subheader(f"Έργο: {selected_project}")
        st.caption(f"Προϋπολογισμός: {proj_info['total_funding']}€ | Υποβολή: {proj_info['proposal_deadline']} | Διάρκεια: {proj_info['date_from']} έως {proj_info['date_to']}")
        
        with st.expander("Επεξεργασία Στοιχείων Έργου"):
            with st.form("edit_project_form"):
                e_funding = st.number_input("Προϋπολογισμός", value=float(proj_info['total_funding']), format="%.2f")
                
                try:
                    e_prop_val = datetime.strptime(proj_info['proposal_deadline'], '%d/%m/%Y').date()
                    e_from_val = datetime.strptime(proj_info['date_from'], '%d/%m/%Y').date()
                    e_to_val = datetime.strptime(proj_info['date_to'], '%d/%m/%Y').date()
                except:
                    today = date.today()
                    e_prop_val, e_from_val, e_to_val = today, today, today
                    
                e_prop = st.date_input("Deadline Υποβολής", value=e_prop_val, format="DD/MM/YYYY")
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    e_from = st.date_input("Έναρξη", value=e_from_val, format="DD/MM/YYYY")
                with col_e2:
                    e_to = st.date_input("Λήξη", value=e_to_val, format="DD/MM/YYYY")
                    
                if st.form_submit_button("Αποθήκευση Αλλαγών Έργου"):
                    conn.execute('UPDATE projects SET proposal_deadline=?, date_from=?, date_to=?, total_funding=? WHERE id=?', 
                                 (e_prop.strftime('%d/%m/%Y'), e_from.strftime('%d/%m/%Y'), e_to.strftime('%d/%m/%Y'), e_funding, proj_info['id']))
                    conn.commit()
                    st.rerun()
        
        ptab1, ptab2, ptab3 = st.tabs(["Συνεργάτες & Εταίροι", "Quarters & Tasks", "Αρχεία"])
        
        with ptab1:
            with st.form("new_stakeholder_form", clear_on_submit=True):
                sh_name = st.text_input("Όνομα Φορέα ή Εταίρου")
                sh_role = st.text_input("Ρόλος (π.χ. Συντονιστής)")
                sh_funding = st.number_input("Προϋπολογισμός Εταίρου", min_value=0.0, format="%.2f")
                
                if st.form_submit_button("Προσθήκη Stakeholder"):
                    if sh_name:
                        conn.execute('INSERT INTO stakeholders (project_name, name, funding, role) VALUES (?, ?, ?, ?)', 
                                   (selected_project, sh_name, sh_funding, sh_role))
                        conn.commit()
                        st.success("Ο συνεργάτης προστέθηκε")
                        st.rerun()
                    
            sh_df = pd.read_sql_query('SELECT * FROM stakeholders WHERE project_name = ?', conn, params=(selected_project,))
            if not sh_df.empty:
                st.write("Λίστα Συνεργατών:")
                for index, row in sh_df.iterrows():
                    col_s1, col_s2, col_s3, col_s4 = st.columns([3, 2, 2, 1])
                    col_s1.write(row['name'])
                    col_s2.write(row['role'])
                    col_s3.write(f"{row['funding']:.2f} €")
                    if col_s4.button("🗑", key=f"del_sh_{row['id']}"):
                        conn.execute('DELETE FROM stakeholders WHERE id = ?', (row['id'],))
                        conn.commit()
                        st.rerun()
                        
                    with st.expander(f"Επεξεργασία {row['name']}"):
                        with st.form(f"edit_sh_{row['id']}"):
                            e_sh_name = st.text_input("Όνομα", value=row['name'], key=f"eshn_{row['id']}")
                            e_sh_role = st.text_input("Ρόλος", value=row['role'], key=f"eshr_{row['id']}")
                            e_sh_funding = st.number_input("Προϋπολογισμός", value=float(row['funding']), format="%.2f", key=f"eshf_{row['id']}")
                            if st.form_submit_button("Αποθήκευση"):
                                conn.execute('UPDATE stakeholders SET name=?, role=?, funding=? WHERE id=?', (e_sh_name, e_sh_role, e_sh_funding, row['id']))
                                conn.commit()
                                st.rerun()
                st.divider()

        with ptab2:
            sh_list = []
            if not sh_df.empty:
                sh_list = sh_df['name'].tolist()
            
            if not sh_list:
                st.info("Πρόσθεσε πρώτα stakeholders στην προηγούμενη καρτέλα")
            else:
                with st.form("new_task_form", clear_on_submit=True):
                    task_sh = st.selectbox("Επιλογή Stakeholder", sh_list)
                    task_q = st.selectbox("Τρίμηνο", ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11", "Q12"])
                    task_desc = st.text_input("Περιγραφή Task ή Παραδοτέου")
                    task_dead = st.date_input("Αυστηρό Deadline Task", format="DD/MM/YYYY")
                    
                    if st.form_submit_button("Προσθήκη Task"):
                        conn.execute('INSERT INTO tasks (project_name, stakeholder_name, quarter, description, deadline) VALUES (?, ?, ?, ?, ?)', 
                                   (selected_project, task_sh, task_q, task_desc, task_dead.strftime('%d/%m/%Y')))
                        conn.commit()
                        st.success("Το task ανατέθηκε")
                        st.rerun()
                    
            tasks_df = pd.read_sql_query('SELECT * FROM tasks WHERE project_name = ? ORDER BY quarter', conn, params=(selected_project,))
            if not tasks_df.empty:
                st.write("Λίστα Tasks:")
                for index, row in tasks_df.iterrows():
                    col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns([1, 2, 3, 2, 1])
                    col_t1.write(row['quarter'])
                    col_t2.write(row['stakeholder_name'])
                    col_t3.write(row['description'])
                    col_t4.write(row['deadline'])
                    if col_t5.button("🗑", key=f"del_task_{row['id']}"):
                        conn.execute('DELETE FROM tasks WHERE id = ?', (row['id'],))
                        conn.commit()
                        st.rerun()
                        
                    with st.expander(f"Επεξεργασία Task: {row['description'][:15]}..."):
                        with st.form(f"edit_task_{row['id']}"):
                            e_task_sh = st.selectbox("Stakeholder", sh_list, index=sh_list.index(row['stakeholder_name']) if row['stakeholder_name'] in sh_list else 0, key=f"etsh_{row['id']}")
                            q_options = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11", "Q12"]
                            e_task_q = st.selectbox("Τρίμηνο", q_options, index=q_options.index(row['quarter']) if row['quarter'] in q_options else 0, key=f"etq_{row['id']}")
                            e_task_desc = st.text_input("Περιγραφή", value=row['description'], key=f"etd_{row['id']}")
                            try:
                                e_td_val = datetime.strptime(row['deadline'], '%d/%m/%Y').date()
                            except:
                                e_td_val = date.today()
                            e_task_dead = st.date_input("Deadline", value=e_td_val, format="DD/MM/YYYY", key=f"etdd_{row['id']}")
                            
                            if st.form_submit_button("Αποθήκευση"):
                                conn.execute('UPDATE tasks SET stakeholder_name=?, quarter=?, description=?, deadline=? WHERE id=?', 
                                             (e_task_sh, e_task_q, e_task_desc, e_task_dead.strftime('%d/%m/%Y'), row['id']))
                                conn.commit()
                                st.rerun()
                st.divider()

        with ptab3:
            with st.form("new_proj_file_form", clear_on_submit=True):
                proj_file = st.file_uploader("Προσθήκη Αρχείου", type=["pdf", "docx", "png", "jpg", "xlsx"])
                if st.form_submit_button("Ανέβασμα Αρχείου Έργου"):
                    if proj_file:
                        save_uploaded_file(proj_file, selected_project)
                        st.success("Το αρχείο αποθηκεύτηκε")
                        st.rerun()
            
            folder_path = os.path.join("uploads", "Projects", create_safe_folder_name(selected_project))
            if os.path.exists(folder_path):
                files = os.listdir(folder_path)
                if files:
                    st.write("Περιεχόμενα Φακέλου:")
                    for f in files:
                        col_f1, col_f2, col_f3 = st.columns([4, 1, 1])
                        col_f1.write(f)
                        
                        file_full_path = os.path.join(folder_path, f)
                        with open(file_full_path, "rb") as file_to_dl:
                            file_content = file_to_dl.read()
                        
                        col_f2.download_button(label="📄", data=file_content, file_name=f, key=f"dl_proj_{f}")
                        
                        if col_f3.button("🗑", key=f"del_proj_{f}"):
                            os.remove(file_full_path)
                            st.rerun()
                            
                    st.divider()
                    st.write("Συγκεντρωτικά Αρχεία Έργου")
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for file_name in files:
                            f_path = os.path.join(folder_path, file_name)
                            if os.path.isfile(f_path):
                                zip_file.write(f_path, arcname=file_name)
                    
                    st.download_button(
                        label="📦 Λήψη όλων των αρχείων",
                        data=zip_buffer.getvalue(),
                        file_name=f"{create_safe_folder_name(selected_project)}_files.zip",
                        mime="application/zip"
                    )
                else:
                    st.write("Ο φάκελος δεν έχει αρχεία ακόμα.")
