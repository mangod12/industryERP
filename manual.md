# KumarBrothers Steel ERP Operator Manual

Last verified: 2026-06-16

This manual is for factory staff, supervisors, store teams, QA teams, dispatch teams, and office users who are new to ERP software. You do not need programming knowledge to use the system.

The system helps the factory keep one shared record of:

- Raw material stock.
- Goods received from vendors.
- Quality checks.
- Production progress through fabrication, painting, dispatch, and completion.
- Customer projects.
- Dispatches to customers.
- Scrap and reusable stock.
- Questions, instructions, and operator messages.

## Start Here

1. Open the system address given by your manager.
2. Enter your username and password.
3. Select **Login**.
4. After login, use the left-side menu to move between pages.

![Login](docs/screenshots/00-login.png)

Important:

- Use only your own login.
- Do not share passwords.
- If your password does not work, ask a Boss or Software Supervisor to reset it.
- If you are using a shared computer, log out before leaving the machine.

## Main Screen

After login, the dashboard is the main overview screen.

![Dashboard](docs/screenshots/01-dashboard.png)

Use the dashboard to quickly answer:

- How much material is available?
- Which jobs are in fabrication, painting, dispatch, or completed?
- Is any stock low?
- Is scrap increasing?
- Are there recent updates or alerts?

If a number looks wrong, do not adjust it from the dashboard. Go to the correct page, such as Raw Materials, Stock Overview, Goods Receipt, Dispatch, or Scrap.

## Basic Navigation

Use the left menu for daily work:

- **Dashboard**: overview of factory status.
- **Raw Materials**: simple stock totals used by older tracking flows.
- **Materials Master**: controlled material catalog for formal stock, GRN, and dispatch.
- **Stock Overview**: physical stock lots and movement history.
- **Goods Receipt**: inward material from vendors.
- **Dispatch**: outward material sent to customers.
- **Tracking**: production stage movement.
- **Drawings**: drawing-based production tracking.
- **Customers**: customer and project records.
- **Scrap**: wasted or rejected material.
- **Reusable Stock**: good leftover material that can be used again.
- **Queries**: questions and clarifications.
- **Instructions**: supervisor instructions for the team.
- **Settings / Profile / Register**: account and system administration.

## Your Role

Your role decides which buttons you can see and use.

| Role | What this role normally does |
| --- | --- |
| Boss | Full access and final approvals. |
| Software Supervisor | User setup and supervised system changes. |
| Store Keeper | Stock, goods receipt, stock picking, and material movement. |
| QA Inspector | Inspect, approve, reject, or hold received material. |
| Dispatch Operator | Prepare and confirm customer dispatches. |
| Fabricator | Update fabrication progress. |
| Painter | Update painting progress. |
| User | View information and perform limited daily tasks. |

If a button is hidden or disabled, your role may not allow that action, or the record may not be ready for that step.

## Safety Rules

This system controls factory records. Treat these actions carefully:

- Do not reset stock unless a Boss or Supervisor has told you to do it.
- Do not approve a GRN until QA is complete for every line.
- Do not confirm dispatch until stock lots and weights are checked.
- Do not mark fabrication complete until the material deduction preview looks correct.
- Do not delete customer or stock records casually.
- If unsure, create a Query or ask your supervisor before approving.

Some high-risk actions ask you to type a confirmation phrase before the system continues. Read the message before typing.

## Daily Workflow

Most factory work follows this path:

1. Create or confirm the customer/project.
2. Add or upload production items.
3. Receive material through Goods Receipt.
4. Complete QA.
5. Approve the GRN so stock lots are created.
6. Move production through fabrication and painting.
7. Prepare dispatch.
8. Confirm dispatch.
9. Record scrap and reusable stock as needed.
10. Use Dashboard to monitor status.

## Raw Materials

Raw Materials is the simple stock page. It is useful for quick shop-floor stock totals and older production tracking flows.

![Raw Materials](docs/screenshots/02-raw-materials.png)

Use this page to:

- Add a material.
- Edit a material name, unit, or stock amount.
- See total, used, and available quantity.
- Manage mappings between Excel material names and system material names.
- Reset total stock or used quantity only when instructed.

How to add a material:

1. Open **Raw Materials**.
2. Select **Add Material**.
3. Enter material name, unit, and total quantity.
4. Save.
5. Check that the new material appears in the table.

High-risk reset:

- **Reset Total Stock** changes the total stock value.
- **Reset Used Qty** changes the consumed quantity.
- The system asks for typed confirmation before sending the reset.
- If you do not understand the effect, cancel and ask a supervisor.

## Materials Master

Materials Master is the formal material catalog. It stores controlled material details such as code, type, grade, size, specification, reorder level, and HSN code.

![Materials Master](docs/screenshots/03-materials-master.png)

Use this page when material must be tracked properly for GRN, stock lots, dispatch, and reports.

Typical use:

1. Open **Materials Master**.
2. Add or edit the material code and name.
3. Select the material type.
4. Enter grade, specification, and dimensions if known.
5. Save.

Good practice:

- Keep material codes consistent.
- Do not create duplicate material names for the same steel section.
- Use clear names that store and production teams recognize.

## Stock Overview

Stock Overview shows physical stock lots. A stock lot is a real batch of material with its own weight, QA status, vendor, location, and movement history.

![Stock Overview](docs/screenshots/04-stock-overview.png)

Use this page to:

- Search stock lots.
- Check current weight.
- Check heat number, batch number, or coil number.
- Open lot details.
- Download visible stock rows as CSV.
- See movement history for a lot.

Important:

- Stock lots should normally change through GRN, production consumption, adjustment, transfer, or dispatch.
- Do not expect Hold or Release buttons to change stock status here. They are disabled until a dedicated lot-status workflow is added.
- Use GRN QA decisions for current quality status changes.

## Goods Receipt

Goods Receipt records material received from vendors. A Goods Receipt Note is usually called a GRN.

![Goods Receipt](docs/screenshots/05-goods-receipt.png)

Use GRN when material enters the factory.

Typical GRN flow:

1. Open **Goods Receipt**.
2. Create or select the vendor.
3. Create a draft GRN.
4. Add material line items.
5. Enter vehicle and weighbridge details if available.
6. Submit for QA.
7. QA Inspector records the result for every line.
8. Select the storage yard, warehouse, or rack.
9. Boss or Admin approves the GRN.
10. The system creates stock lots.

Before approving a GRN, check:

- Vendor is correct.
- Material is correct.
- Weight is correct.
- QA status is complete for every line.
- Location is correct.

The system blocks approval until required steps are done. If a GRN is already approved and someone retries, the system will not create duplicate stock lots.

## Dispatch

Dispatch records stock sent out to a customer.

![Dispatch](docs/screenshots/06-dispatch.png)

Typical dispatch flow:

1. Open **Dispatch**.
2. Create a dispatch note for the customer.
3. Add stock lots manually or use FIFO picking.
4. Check vehicle, driver, transporter, and weight details.
5. Submit the dispatch for approval.
6. Confirm dispatch.
7. The system reduces stock through stock movements.

Before confirming dispatch, check:

- Customer is correct.
- Stock lot numbers are correct.
- Weight is correct.
- Vehicle and driver details are correct.
- Dispatch note is submitted for approval.

The system locks picking after Draft stage. It also prevents repeated approval from deducting stock twice.

## Production Tracking

Production Tracking is the shop-floor board for work moving through the factory.

![Production Tracking](docs/screenshots/07-production-tracking.png)

The normal stages are:

1. Fabrication.
2. Painting.
3. Dispatch.
4. Completed.

Use this page to:

- Search for a job.
- Filter by customer or stage.
- Start work on a stage.
- Complete a stage.
- Review current production load.

Fabrication completion:

- When fabrication is completed, the system opens a material deduction preview.
- Read the preview carefully.
- Confirm only if the material and quantity look correct.
- The item does not move to the next stage until this confirmation is accepted.

If a job is not moving:

- Check whether the current stage was started.
- Check whether required checklist items are complete.
- Check your role permissions.
- Ask a supervisor if the item appears stuck.

## Drawings And Production

Drawings is for engineering-based tracking. It connects drawings, assemblies, components, and component instances.

![Drawings](docs/screenshots/08-drawings.png)

Use this page when work must be controlled by drawing number instead of only a customer item.

Simple meaning of the drawing structure:

- **Drawing**: the engineering drawing or package.
- **Assembly**: a group inside the drawing.
- **Component**: a part such as beam, column, plate, bracket, or channel.
- **Component Instance**: the actual piece being made.
- **Stage Transition**: the movement of that piece through production stages.

Use consistent drawing numbers so everyone can find the same work.

## Customers

Customers stores customer and project records.

![Customers](docs/screenshots/09-customers.png)

Use this page to:

- Add a customer or project.
- Review active projects.
- Open customer details.
- Upload or review production data tied to a customer.
- Keep production work grouped by project.

Before deleting a customer record, check with a Boss or Supervisor. Customer records may be connected to production items, drawings, dispatches, and reports.

## Customer Detail

Customer Detail shows one customer/project in detail.

![Customer Detail](docs/screenshots/17-customer-detail.png)

Use this page to:

- Review project information.
- Review linked production work.
- Check stage history.
- Confirm that uploaded work belongs to the right customer.

## Scrap

Scrap records material loss.

![Scrap](docs/screenshots/10-scrap.png)

Use Scrap when material is wasted because of cutting, damage, rejection, mistake, leftover unusable size, or other loss.

Record:

- Material.
- Weight.
- Quantity.
- Reason.
- Source customer or production item if known.
- Estimated value if available.

Good scrap recording helps the factory understand real loss and reduce waste.

## Reusable Stock

Reusable Stock tracks leftover material that is still usable.

![Reusable Stock](docs/screenshots/11-reusable.png)

Use this page when an offcut or leftover piece can be used later instead of being treated as scrap.

Record enough detail so another worker can find and use the material:

- Material name.
- Size or dimensions.
- Weight or quantity.
- Location.
- Source if known.

## Queries

Queries are questions or clarifications.

![Queries](docs/screenshots/12-queries.png)

Use Queries when:

- A drawing or instruction is unclear.
- A production step needs approval.
- A material mismatch needs a decision.
- A customer requirement needs clarification.

Queries keep decisions visible in the system instead of only in calls or chat messages.

## Instructions

Instructions are supervisor messages for the team.

![Instructions](docs/screenshots/13-instructions.png)

Use Instructions for:

- Priority changes.
- Urgent dispatch reminders.
- QA notes.
- Shop-floor directions.
- General announcements.

Read instructions at the start of each shift.

## Settings, Users, And Profile

Settings contains account and system options.

![Settings](docs/screenshots/14-settings.png)

Boss and Software Supervisor roles can create users.

![Register User](docs/screenshots/15-register-user.png)

When creating a user:

1. Open **Register User**.
2. Enter name, email, password, company, and role.
3. Choose the correct role.
4. Save.
5. Tell the user their username and password privately.

Profile shows your account and password controls.

![Account Profile](docs/screenshots/16-account-profile.png)

Use Profile to:

- Review your account.
- Change your password if allowed.
- Log out safely.

## Common Problems

| Problem | What to do |
| --- | --- |
| Login fails | Check username and password. Ask a supervisor to reset your password. |
| Button is disabled | Finish the previous step, check required fields, or confirm your role has permission. |
| Page does not update | Refresh the page once. If still wrong, report it to a supervisor. |
| Wrong stock quantity | Do not guess. Check Stock Overview, Goods Receipt, Dispatch, and Raw Materials history. |
| GRN cannot be approved | Check QA status for every line and confirm a location is selected. |
| Dispatch cannot be confirmed | Check that it is submitted, stock lots are picked, and weights are valid. |
| Production item will not move | Check checklist, current stage, and role permission. |
| Material deduction looks wrong | Cancel the action and ask a supervisor before confirming. |
| Customer is missing | Search by alternate spelling or project name. If missing, create a new customer only after confirming it is not a duplicate. |

## Shift Checklist

At the start of a shift:

1. Log in.
2. Read Instructions.
3. Check Dashboard.
4. Review your assigned page: Store, QA, Tracking, Dispatch, or Production.
5. Check open Queries.

During the shift:

1. Update work as it happens.
2. Use the correct page for each action.
3. Confirm high-risk actions carefully.
4. Raise a Query when a decision is unclear.

At the end of a shift:

1. Finish pending updates.
2. Check Dashboard for obvious mistakes.
3. Log out.
4. Tell the next shift about open issues.

## Glossary

| Word | Meaning |
| --- | --- |
| ERP | The shared factory software system. |
| GRN | Goods Receipt Note, used when material comes into the factory. |
| Stock Lot | A physical batch of material with its own weight and traceability. |
| QA | Quality Assurance, the team or process that checks material quality. |
| FIFO | First In, First Out. Older stock is picked before newer stock. |
| Dispatch | Material or finished work sent to a customer. |
| Scrap | Material loss or unusable leftover. |
| Reusable Stock | Leftover material that can still be used later. |
| Query | A question or clarification raised in the system. |
| Stage | A production step such as fabrication, painting, dispatch, or completed. |

## When To Ask For Help

Ask a Boss, Software Supervisor, or system owner for help when:

- You cannot log in.
- Your role does not show a button you need.
- Stock quantity looks wrong.
- A GRN, dispatch, or production item appears stuck.
- A material deduction preview does not match the physical work.
- You are unsure whether to approve, reset, delete, or confirm something.

Do not force a workaround outside the system. Raise a Query or inform your supervisor so the decision is recorded.
