# Filevine User Termination Procedure

This document outlines the full process for terminating a Filevine user, removing access across systems, and ensuring hardware is properly handled.

---

## 1. Remove Employee Okta and SSO Access

**Responsibility:** IT Team manages account termination and transfer processes in Okta.

1. Mark the user’s asset tag and SN in the **tags** section of their termination ticket.  
2. Perform at the end of their last day unless otherwise noted.  
3. In **Okta Admin > Directory > People**:
   - Locate the user.
   - **More actions → Clear user sessions → Clear all sessions.**
   - **More actions → Deactivate.**  
     ![Deactivate Screenshot](https://content.api.getguru.com/files/view/9a733e2f-974c-49c8-823d-fc7e064c0435)

---

## 2. Remove Common Standalone Application Access

### Microsoft

#### Exchange
- Go to [Exchange Admin Center](https://admin.exchange.microsoft.com/#/).
- Recipients → Mailboxes.
- Find user → Convert to shared mailbox.
- Under **Delegation**, add requested user to all fields.

#### M365
- Go to [M365 Admin Center](https://admin.microsoft.com/Adminportal/Home?#/homepage).
- Users → Active Users.
- Open user profile → **Licenses and apps** → Uncheck all → Save changes.
- In Okta, remove from **SSO-Microsoft 365 E3 - User** group.

---

### Google

- **Critical Employees:** Change Org Unit to *terminated* instead of deletion, then remove license manually.
- Directory → Users → Search user.
- Select user → **More options → Delete selected users.**
- Under **Data in other apps**, select **Transfer** → assign to manager.
- Click **Delete User**.
- Remove from **SSO-G Suite_EnterpriseUsers** group in Okta after confirming data backup.

---

### Zoom

- Log into Zoom via Okta.
- Admin → User Management → Users.
- Search email → 3-dot menu → Delete.
- Assign manager email for data transfer.
- If webinar data transfer required, ensure both accounts are in the proper Okta groups.
- Click **Transfer Data Then Delete**.
- Remove from Zoom groups:
  - `SSO-Zoom_Member_Basic`
  - `SSO-Zoom_Member_Pro`
  - `SSO-Zoom_Member_Pro_Phone`

---

### Domo
- Log into Domo Admin via Okta.
- Select user → **Delete person**.
- Remove from **SSO-Domo** group in Okta.

### Lucidchart
- Log into Lucidchart Admin.
- Users → Search user → Delete user.
- Transfer documents to manager if required.
- Remove from **SSO-LucidChart** group in Okta.

### SynQ (Annual Review)
- Log into SynQ Admin.
- Search user → Trash can icon → Delete.

### Adobe
- Log into [Adobe Admin](https://adminconsole.adobe.com/E0702CB358BDC27A0A495C70@AdobeOrg/overview).
- Users → Search user.
- Remove products under **Edit products**.
- Remove from **SSO-Adobe** group in Okta.

### Workato
- Log into Workato via Okta.
- Workspace Admin → Search collaborator.
- Delete collaborator.
- Remove from all **SSO-Workato** groups.

---

## 3. EntraID / Microsoft Endpoint Manager

### For CJIS Employees
- Log into Intune (via Microsoft Admin).
- Devices → All Devices → Search system → Retire → Restart laptop.
- Users → Search → Delete.

### For Non-CJIS Employees
- Ensure laptop will check in on restart.
- No further action required.

---

## 4. Laptop Wiping

### Reusable Laptops
- Update [IT Inventory spreadsheet](https://docs.google.com/spreadsheets/d/1_ZP2-oQYql65hWa7YvUknL3ElZ42j9GFFSL4LciZcLk/edit#gid=374717709).

**If CJIS Access:**
- Hard Drive → Secure erase with 3-pass overwrite (NIST 800-88).  
- SSD → Secure erase (NIST 800-88).  

Prepare for reuse.

### Non-Reusable Laptops
- Record serial number.
- Prepare for delivery to TAMS.
- Secure erase drives (per NIST 800-88) if CJIS access was present.

---

## 5. SolarWinds Asset Update

- Open SolarWinds Service Desk.
- Inventory → Computers → Search asset.
- Change **Asset Status → Spare**.  
  ![Screenshot](https://content.api.getguru.com/files/view/9fce3a46-7803-4769-9766-59736738fe24)
- Remove user as owner → Assign to Inventory.

---

## 6. Kandji (Mac)

- Open Kandji → Search device.
- Update:
  - **User field → Not assigned**  
    ![Screenshot](https://content.api.getguru.com/files/view/c630d1e3-29eb-4aed-9b23-4501b0e19419)
  - **Blueprint field → Inventory Only**  
    ![Screenshot](https://content.api.getguru.com/files/view/008f7f04-d78a-471b-b4b0-776f27f44dd1)

---

## 7. Intune (Dell)

- Open Intune Admin Center.
- Search device → Properties → **Remove Primary user**.

---

## 8. Non-IT Administered Services

The following are **not managed by IT** and require action by HR or other departments:

- Paylocity (HR)  
- Salesforce, Outreach, Salesloft, Clari, ZoomInfo, Gong, Chorus, GTM Buddy (RevOps)  
- 4MyBenefits, Culture Amp (HR)  
- Lever (Recruiting)  
- Incident IO, New Relic (R&D)  
- KnowBe4 (manual removal in app)  

⚠️ **HR must notify Compliance immediately if terminated employee had CJIS clearance** (removal within 24 hours).

---


