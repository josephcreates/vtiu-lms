# VTIU Backend Sync Audit Report

This report summarizes the findings of the logical and structural audit between the **Ktor (Mobile Engine)** and **Flask (Web/CMS)** backends.

## 1. Core Sync Status

| Module | Status | Findings |
| :--- | :--- | :--- |
| **Authentication** | ✅ Synced | Both use the `user` table and UUID-based `public_id`. Android session management is compatible with Flask's `User` model. |
| **Live Classroom** | ✅ Synced | Both now use the 6-character normalized alphanumeric Room IDs. Agora channel names are consistent. |
| **Real-time Chat** | ⚠️ Mismatch | **Action Required**: Ktor sends a flat JSON object (`ChatMessageApi`), but the Flask Redis bridge expects a nested structure. |
| **Fee Management** | ⚠️ Logic Divergence | **Action Required**: Ktor's Paystack processor uses different default academic year logic than Flask's `configured_academic_year()`. |
| **Assignments** | ✅ Synced | Both backends query the same `assignment` table. No discrepancies found in submission storage. |

---

## 2. Technical Discrepancies & Risks

### A. Chat Bridge Payload Mismatch
*   **Ktor sends**: `{"sender_id": "...", "message": "...", "timestamp": "..."}`
*   **Flask bridge expects**: `{"message": {"content": "...", "sender_name": "..."}}`
*   **Impact**: Messages sent from Android appear as "Unknown" or fail to display on the Web Dashboard.

### B. Financial Year Logic
*   **Flask**: Centralized via `utils/academic_year.py` and `configured_academic_year()`.
*   **Ktor**: Uses `LocalDate.now().year` as a fallback.
*   **Impact**: If a payment is made on Dec 31st for the next year, Ktor might log it to the wrong academic cycle.

### C. Date Formatting
*   **Ktor**: Uses `kotlinx-datetime` (ISO 8601 by default).
*   **Android App**: Some screens expect `yyyy-MM-dd HH:mm:ss`.
*   **Impact**: Potential parsing errors in older Android versions if the `T` separator is present.

---

## 3. Mandatory Remediation Steps

### Step 1: Fix Chat Bridge (Flask)
Update `chat_routes.py` to handle the flat `ChatMessageApi` format sent by Ktor.

### Step 2: Sync Academic Year (Ktor)
Modify `FinanceRoutes.kt` to query the `school_setting` table for the `current_academic_year` instead of relying on the system clock.

### Step 3: Standardize ID Normalization
Ensure both backends use the `filter { it.isLetterOrDigit() }` logic for all Room ID comparisons to handle any accidental dashes in the database.

---

## 4. Final Recommendation
**Continue with the Bridged Architecture.** The discrepancies identified are minor implementation details and do not require an architectural overhaul. Ktor remains the best choice for high-speed mobile traffic, while Flask provides the necessary Web UI and Admin tooling.
