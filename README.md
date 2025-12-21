## 📎 File Submission & Centralized Admin Upload Process

The **Work Submission Tracker & Indicator System** is a **web-based application** built using **Django, JavaScript, HTML, CSS, and PostgreSQL**.  
It implements a **centralized file submission workflow** where **only the designated Admin** performs the final document uploading.

All documents prepared by **focal persons and sub-sections** are first collected under their respective sections and are **officially uploaded in bulk by the Section/Admin user**.

This approach ensures document integrity, consistency, and accountability.

---

## 🛠️ Technologies Used

- **Backend:** Django (Python)
- **Frontend:** HTML, CSS, JavaScript
- **Database:** PostgreSQL
- **Architecture:** Server-side rendered web system with role-based access control

---

### 🗂️ Centralized Upload Policy

- Focal persons and sub-section units **do not directly upload** final documents to the system
- All section-related documents are **submitted to the Section Admin**
- The **Admin performs bulk upload** on behalf of the entire section
- Uploaded files represent the **official and validated submission**

---

### 🧭 Upload Routing Logic

The upload destination is determined by:

- The assigned **Work Cycle**
- The **Section / Unit**
- The **Admin role**
- The associated **Work Item(s)**

All files uploaded by Admin are stored under the **section-specific folder** for that work cycle.

---

### 🧑‍💼 Role Responsibilities

| Role | Responsibility |
|------|---------------|
| Focal Person | Prepare documents and submit to Section Admin |
| Sub-Section Unit | Consolidate internal files |
| Section Admin | Validate, consolidate, and upload files in bulk |
| System Admin | System oversight and audit access |

Only **Admin-level users** have permission to upload files to the system.

---

### 🔐 Security & Audit Controls

- All uploaded files are:
  - Uploaded by an Admin account
  - Timestamped and user-attributed
- Bulk uploads are logged as a single submission action
- Files are linked to:
  - The relevant **Work Cycle**
  - The related **Work Item(s)**
- Uploaded files become **read-only** after submission
- Replacement or deletion requires Admin authorization

---

### 🔄 Bulk Submission Workflow

1. Focal persons prepare and submit documents offline to Section Admin
2. Section Admin validates and consolidates files
3. Admin performs **bulk upload** to the system
4. Files are linked to corresponding work items
5. Reviewer accesses files for evaluation
6. Files are archived after completion

---

### 📌 Advantages of Centralized Admin Upload

- Ensures a single source of truth
- Prevents duplicate or incorrect submissions
- Standardizes document format and naming
- Simplifies review and auditing
- Aligns with PENRO operational procedures
