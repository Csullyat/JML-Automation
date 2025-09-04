# Filevine New User Setup Procedure

This document provides the standard operating procedure (SOP) for creating and configuring a new Filevine employee or contractor in **Okta**.  
All information is pulled from the onboarding ticket in SolarWinds.

---

## 1. Creating the User in Okta

1. On the **Okta dashboard**, click **Admin** (top right).
2. In the left navigation pane, select **Directory → People**.
3. Click **Add person**.
4. Fill out the details using the ticket:

### Required Fields

- **First & Last Name**  
  - Use the *New Employee Name* field from the ticket.

- **Username**  
  - Format: `{firstname}{lastname}@filevine.com` (no spaces).  
    - Example: `johndoe@filevine.com`  
  - For contractors: `{firstname}.{lastname}@filevine.com`.  
    - Example: `mary.jane@filevine.com`  
  - Notify Facilities if the contractor hire is **off-cycle**.

- **Primary Email**  
  - Auto-generated from the Username.

- **Secondary Email**  
  - Use the *New Employee Personal Email Address* field.

- **Groups**  
  - Add:
    - `Filevine Employees`
    - `SSO-Zoom_Member_Basic`  
      - Use `SSO-Zoom_Member_Pro` if they are an AE.
    - Department group (based on *New Employee Department*).
    - Any other groups required by the role.

- **Activation**  
  - Set to **Activate now**.

5. Click **Save**.

---

## 2. Adding Profile Details

1. Navigate to **Directory → People**, search for the new user, and click their name.
2. Go to the **Profile** tab and click **Edit**.
3. Fill out the following using ticket details:

- **Title**  
  - Use *New Employee Title*.  
  - If a contractor: `"Title – Contractor"`.

- **Display Name**  
  - Use *New Employee Name*.

- **Mobile Phone**  
  - Use *New Employee Phone Number*.  
  - Format: `xxx-xxx-xxxx`.

- **Primary Phone**  
  - If Zoom phone required: enter the Zoom number.  
    - See [Giving a User a Zoom Phone Number](https://app.getguru.com/card/iqRELroT/Giving-a-User-a-Zoom-Phone-Number).  
  - If user requests their phone be in their signature: add it here.  
  - Otherwise, leave blank.

- **Address (Street / City / State / Zip / Country)**  
  - Use *New Employee Mailing Address*.  
  - State: two-letter abbreviation (e.g., `UT`).  
  - Country: two-letter abbreviation (e.g., `US`).

- **Preferred Language**  
  - Two-letter code (e.g., `en`).

- **Time Zone**  
  - Use [tz_database format](https://www.timetemperature.com/tzus/time_zone.shtml).  
  - Common options:
    - Eastern → `America/New_York`
    - Central → `America/Chicago`
    - Mountain → `America/Denver`
    - Pacific → `America/Los_Angeles`

- **Organization**  
  - Always `Filevine`.

- **Department**  
  - Use *New Employee Department*.

- **Manager ID**  
  - Use the *Reports To* field.  
  - Format: `{lastname}, {firstname}`.

- **Manager**  
  - Hover over the “Reports To” name in the ticket and copy the manager’s email.

- **SolarWinds Role**  
  - Set to `Requester`.

- **Primary**  
  - Set to `True`.

4. Click **Save**.

---

## 3. Verify Okta Tasks & Application Assignments

1. On the **Okta Dashboard**, go to the **Tasks** page.
2. Check for **Application assignments encountered errors**.
3. For each application (Zoom, Microsoft, Google, etc.):
   - Select the app.
   - Click **Retry Selected**.
   - Click **Refresh** to confirm the licenses are now applied.

---

✅ **At this point, the new user account is fully provisioned in Okta.**
