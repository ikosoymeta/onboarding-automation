# Vendor Onboarding Automation Skill - Infographic Overview

**For:** NotebookLM Infographic Generation  
**Skill:** Vendor Onboarding Automation v2.0  
**Purpose:** Visual guide for users to understand skill capabilities and commands

---

## 🎯 Skill Overview (Header Section)

**Title:** Vendor Onboarding Automation Skill  
**Subtitle:** AI-Powered Procurement & Vendor Management for Meta  
**Version:** 2.0 (June 2026)  
**Tagline:** "From vendor onboarding to purchase requests — automated through conversational AI"

**Key Stats (Visual Callouts):**
- 7+ Systems Integrated (Buy@, Butterfly, CSC, AMP, TPA, etc.)
- 12 Trigger Phrases
- 6 MCP Tools Enabled
- 2 Main Workflows (Vendor Onboarding + PR Creation)
- 47+ Buy@ MCP Tools Available via AI

---

## 🏗️ Architecture (Visual Diagram)

**Center:** Metamate Chat Interface  
**Connected to:** Buy@ Assistant (AI Agent Hub)  
**Buy@ Assistant Routes To:**
- BUY_SUPPLIER_AGENT → Supplier operations
- BUY_PURCHASING_AGENT → PR operations (NEW)
- 47+ MCP Tools

**Systems Integrated (Icons around the center):**
- 🏢 Buy@ (Supplier & PR Management)
- 🦋 Butterfly (Forms & Approvals)
- 👥 CSC (Worker Onboarding)
- 🔐 AMP (Access Management)
- 🛡️ TPA (Security Assessment)
- 📧 Notifications (Workplace & Email)

---

## 📦 Capability Categories (Two Main Pillars)

### Pillar 1: Vendor Onboarding (Left Side)
**Icon:** 👥 People/Onboarding  
**Color:** Blue (#1877F2 - Meta Blue)

**What It Does:**
- Automates complete vendor onboarding workflow
- Guides users through conversational data collection
- Validates information in real-time
- Orchestrates system interactions
- Provides status updates and notifications

**Key Features:**
- ✅ Duplicate supplier detection via AI
- ✅ Supplier onboarding via Buy@ Assistant
- ✅ Bulk worker onboarding via spreadsheet
- ✅ AMP group management
- ✅ TPA security assessment initiation
- ✅ Proactive notifications

**Workflow Steps (Visual Flow - Top to Bottom):**
1. **Initiate** → User provides vendor name
2. **Verify** → AI checks Buy@ for existing supplier
3. **Collect** → Conversational data gathering
4. **Validate** → Real-time field validation
5. **Execute** → Parallel system orchestration
6. **Monitor** → Status tracking & notifications

**Time Saved:**
- Existing active supplier: **~1 week saved** (skip onboarding)
- New supplier: **~2-3 weeks** (automated vs manual)

---

### Pillar 2: Purchase Request Creation (Right Side) [NEW]
**Icon:** 🛒 Shopping Cart / PR  
**Color:** Green (#00A400 - Success Green)  
**Badge:** "NEW in v2.0"

**What It Does:**
- Creates Purchase Requests via Buy@ Assistant
- Two modes: Draft (for review) or Direct Submission (with monitoring)
- Real-time PR status tracking
- Async monitoring with notifications
- Document attachment support

**Key Features:**
- ✅ PR Draft Creation — for user review before submission
- ✅ Direct PR Submission — immediate entry to approval workflow
- ✅ PR Status Tracking — real-time approval chain visibility
- ✅ Document Attachments — PDF, DOCX, XLSX, images
- ✅ Supplier Validation — existence, active status, TPA checks
- ✅ Async Monitoring — background polling with notifications
- ✅ 3 NEW MCP Tools — Update, Justification, Search

**PR Creation Modes (Side-by-Side Comparison):**

| Draft Mode | Direct Submission Mode |
|------------|------------------------|
| 📝 Creates PR as draft | 🚀 Submits immediately to approval |
| 👀 User reviews in Buy@ UI | ⚡ Enters workflow right away |
| ✋ User manually submits | 🤖 Async monitoring starts automatically |
| 🎯 Best for: Complex PRs | 🎯 Best for: Straightforward PRs |
| ⏱️ User controls timing | 🔔 Notifications on status changes |

**PR Lifecycle (Visual Flow):**
```
User Request → Supplier Validation → PR Creation → 
    ├─→ Draft Mode → User Review → Manual Submit
    └─→ Submit Mode → Approval Workflow → Async Monitoring → 
        ├─→ Approved → PO Generated → ✅ Notification
        └─→ Rejected → Reason Provided → ❌ Notification
```

---

## 💬 Metamate Commands (Command Reference Section)

### Vendor Onboarding Commands (5 commands)
**Category:** 👥 Vendor Management  
**Icon:** Person with plus sign

1. **"I need to onboard [Vendor Name] as a vendor"**
   - Most explicit, includes vendor name
   - Example: "I need to onboard Acme Corp as a vendor"

2. **"Onboard a vendor"**
   - Simple trigger, skill asks for details
   - Good for starting conversation

3. **"Onboard a supplier"**
   - Alternative phrasing, same as vendor
   - Supplier = Vendor in Meta terminology

4. **"Start vendor onboarding for [Vendor Name]"**
   - Explicit action-oriented phrasing
   - Example: "Start vendor onboarding for Acme Corp"

5. **"Help me onboard [Vendor Name]"**
   - Help-seeking phrasing
   - Example: "Help me onboard Acme Corp"

**Follow-up Commands:**
- "What's the status of [Vendor Name] onboarding?"
- "Check status for [Vendor Name]"
- "Where are we with [Vendor Name]?"

---

### Purchase Request Commands (7 NEW commands)
**Category:** 🛒 Procurement  
**Icon:** Shopping cart or document with dollar sign  
**Badge:** "NEW"

**Create PR Commands:**
1. **"Create a purchase request for [Supplier]"**
   - General PR creation, skill asks for details
   - Example: "Create a purchase request for Acme Corp"

2. **"Create a PR for [Supplier]"**
   - Abbreviated version, same as above
   - Example: "Create a PR for Acme Corp"

3. **"Create a PR draft for [Supplier]"**
   - Explicitly requests draft mode
   - Example: "Create a PR draft for Acme Corp"

4. **"Submit a PR for [Supplier]"**
   - Explicitly requests direct submission mode
   - Example: "Submit a PR for Acme Corp"

5. **"Create a PR for [Supplier] for $[Amount]"**
   - Includes amount upfront, faster flow
   - Example: "Create a PR for Acme Corp for $5000"
   - Example: "Create a PR for Acme Corp for $10,000"

**Status Check Commands:**
6. **"Check status of PR [PR Number]"**
   - Check specific PR by number
   - Example: "Check status of PR-12345"
   - Example: "Check status of PR-67890"

7. **"What's the status of my purchase request?"**
   - General status inquiry
   - Skill may ask which PR or show recent PRs

**Advanced PR Commands (via API):**
- "Update PR [Number]" - Modify existing PR
- "Generate justification for PR" - AI writing help
- "Search PRs" - Find PRs by criteria

---

## 🔧 MCP Tools Enabled (Technical Details Section)

**Total:** 6 Buy@ MCP Tools

### Supplier Management Tools (2)
1. **MetamateAgentBuyAtSupplierSearchTool**
   - Search suppliers by name
   - Check existence and status
   - Get supplier ID and details

2. **MetamateAgentBuyAtSupplierOnboardingTool**
   - Invite new suppliers to Buy@
   - Initiate onboarding workflow
   - Send enrollment emails

### Purchase Request Tools (4 - 3 NEW)
3. **MetamateAgentBuyAtPurchaseRequestDraftCreateTool**
   - Create PR drafts from natural language
   - Extract data from attachments
   - Support draft and submission modes

4. **MetamateAgentBuyAtPurchaseRequestUpdateTool** ⭐ NEW
   - Update existing PRs
   - Modify quantities, prices, line items
   - Change delivery dates

5. **MetamateAgentBuyAtPurchaseRequestJustificationTool** ⭐ NEW
   - Generate AI-powered business justifications
   - Improve PR approval speed
   - Ensure compliance with requirements

6. **MetamateAgentBuyAtPurchaseRequestSearchTool** ⭐ NEW
   - Search PRs by supplier, status, date, amount
   - Find historical PRs
   - Rich filtering capabilities

---

## 📊 Workflow Comparison (Visual Table)

| Aspect | Vendor Onboarding | PR Creation |
|--------|------------------|-------------|
| **Trigger** | "Onboard [Vendor]" | "Create PR for [Supplier]" |
| **Duration** | 1-3 weeks | Minutes to create, days to approve |
| **Systems** | Buy@, Butterfly, CSC, AMP, TPA | Buy@ only |
| **Key Output** | Active supplier + onboarded workers | PR number + approval workflow |
| **Monitoring** | Milestone notifications | Real-time status polling |
| **Best For** | New vendors, worker onboarding | Purchasing goods/services |

---

## 🎨 Visual Design Elements for Infographic

**Color Scheme:**
- Primary: Meta Blue (#1877F2) - Vendor Onboarding
- Secondary: Success Green (#00A400) - PR Creation (NEW)
- Accent: Purple (#8B5CF6) - AI/Metamate
- Neutral: Gray (#6B7280) - Text and backgrounds
- Warning: Orange (#F59E0B) - Blockers and issues

**Icons:**
- Vendor Onboarding: 👥 (people), 🏢 (building), ✅ (checkmark)
- PR Creation: 🛒 (cart), 📄 (document), 💰 (money)
- AI: 🤖 (robot), ✨ (sparkles), 🧠 (brain)
- Status: ⏳ (pending), ✅ (complete), ❌ (error), ⚠️ (warning)
- Actions: 🔍 (search), 📤 (submit), 📎 (attachment), 🔔 (notification)

**Layout Suggestion:**
1. **Top:** Skill title and version badge
2. **Middle:** Two pillars side-by-side (Vendor Onboarding left, PR Creation right)
3. **Bottom:** Command reference table
4. **Footer:** Skill URL and contact info

**Callout Boxes:**
- "NEW in v2.0" badge on PR Creation pillar
- "Saves 1 week" callout for existing suppliers
- "47+ MCP Tools" badge for Buy@ Assistant
- "Thread-Safe" and "Memory Safe" badges for technical reliability

---

## 🔗 Quick Reference

**Skill URL:** https://metamate.internalmeta.com/skills/vendor-onboarding-automation  
**GitHub:** https://github.com/ikosoymeta/onboarding-automation  
**Documentation:** 
- METAMATE_SKILL.md (full skill definition)
- SKILL_OVERVIEW.md (comprehensive overview)
- FAQ_TROUBLESHOOTING.md (user guide)

**Contact:**
- Maintainer: Igor Kosoy (ikosoy@meta.com)
- Team: BO&SS: Operations
- Oncall: RL Content Org Tools

**Version:** 2.0 (June 2026)  
**Status:** Ready for Metamate Registry Deployment
