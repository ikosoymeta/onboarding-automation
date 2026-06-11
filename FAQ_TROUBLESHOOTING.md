# Vendor Onboarding Skill - FAQ and Troubleshooting Guide

**Version:** 2.0 (June 2026)  
**For:** Vendor Onboarding Automation with PR Creation  
**Contact:** Igor Kosoy (ikosoy@meta.com) | BO&SS: Operations

## Frequently Asked Questions (FAQ)

### General Questions

**Q: What is the Vendor Onboarding Automation Skill?**
A: It's a Metamate-powered conversational assistant that automates vendor onboarding and Purchase Request (PR) creation at Meta. It guides you through data collection, validates information, orchestrates system interactions across 7+ Meta systems (Buy@, Butterfly, CSC, AMP, TPA), and provides real-time status updates.

**Q: What's new in Version 2.0 (June 2026)?**
A: Version 2.0 adds:
- **Buy@ Assistant Integration** - AI-powered supplier verification and onboarding via Metamate agents
- **Purchase Request Creation** - Automated PR creation with draft and direct submission modes
- **PR Status Monitoring** - Real-time tracking of PR approval workflow with notifications
- **Document Attachments** - Upload quotes, SOWs, and supporting documents to PRs

**Q: Do I need any special permissions to use the skill?**
A: No. The skill uses your existing SSO session and respects your current permissions in Buy@, Butterfly, CSC, AMP, and TPA. If you can access these systems manually, the skill can automate them for you.

**Q: Is my data secure?**
A: Yes. The skill:
- Uses your SSO session (no separate credentials stored)
- Sanitizes PII in logs (emails are masked)
- Stores screenshots with restricted permissions (0700)
- Clears sensitive data from memory after use
- Maintains complete audit trail for compliance
- All API calls stay within Meta network

### Vendor Onboarding Questions

**Q: How do I start onboarding a vendor?**
A: Simply tell Metamate:
- "I need to onboard Acme Corp as a vendor"
- "Onboard a vendor"
- "Start vendor onboarding for [Vendor Name]"

The skill will guide you through the process step by step.

**Q: How long does vendor onboarding take?**
A: Timeline depends on several factors:
- **Supplier already in Buy@ and active:** ~1-2 weeks (saves 1 week vs new supplier)
- **New supplier:** ~2-3 weeks (includes 10-day supplier enrollment period)
- **With TPA required:** Add 3-5 business days for security assessment
- **With workers:** Add time for CSC processing (varies by worker count)

The skill provides estimated completion dates based on historical data.

**Q: What if the supplier is already in Buy@?**
A: The skill automatically checks Buy@ via the Buy@ Assistant. If the supplier exists and is active, it skips the supplier onboarding step (saving about 1 week) and proceeds directly to worker onboarding and access setup.

**Q: What if the supplier exists but is inactive?**
A: The skill will detect the inactive status and guide you through the reactivation process via Buy@ Assistant. This is faster than onboarding a completely new supplier.

**Q: What information do I need to provide?**
A: The skill will ask for:
- **Supplier Information:** Legal name, contact email, business purpose, estimated spend
- **Worker Information:** For each worker - name, email, job title, dates, location, manager
  - Or upload a spreadsheet with all workers
- **Access Requirements:** Systems needed (GitHub, AWS, etc.), YubiKey needs

The skill validates data in real-time and provides clear error messages.

**Q: Can I onboard multiple workers at once?**
A: Yes! You can upload a spreadsheet with all worker details. The skill validates the spreadsheet and processes all workers in bulk via CSC. See the User Guide for spreadsheet template.

**Q: How do I check the status of an onboarding?**
A: Ask Metamate:
- "What's the status of Acme Corp onboarding?"
- "Check status for [Vendor Name]"

You'll get a detailed progress report with completed steps, pending items, and estimated completion date.

### Purchase Request (PR) Creation Questions

**Q: What's the difference between PR Draft mode and Direct Submission mode?**
A:
- **Draft Mode:** Creates PR as a draft for your review. You manually review and submit via Buy@ UI when ready. Best for complex PRs requiring careful review.
- **Direct Submission Mode:** Creates PR and submits immediately to approval workflow. The skill monitors status and notifies you of changes. Best for straightforward PRs.

**Q: How do I create a PR?**
A: Tell Metamate:
- "Create a PR for Acme Corp"
- "Create a PR draft for [Supplier]"
- "Submit a PR for [Supplier] for $[Amount]"

The skill will guide you through providing: supplier name, amount, description, business justification, cost center, and optional attachments.

**Q: What if the supplier is not in Buy@?**
A: The skill checks supplier status before creating a PR. If the supplier is not found or inactive, it will inform you and offer to:
1. Invite the supplier to Buy@ first (takes ~1 week), OR
2. Choose a different supplier that already exists

You cannot create a PR for a supplier that doesn't exist in Buy@.

**Q: What is TPA and why does it block PR creation?**
A: TPA (Third Party Assessment) is Meta's security and compliance review for suppliers. If a supplier's TPA has expired or is not active, the skill will block PR submission until TPA is renewed. This is a compliance requirement.

**Q: Can I attach documents to a PR?**
A: Yes! When creating a PR, you can attach:
- Quotes (PDF)
- Statements of Work (DOCX, PDF)
- Contracts
- Other supporting documents (images, spreadsheets)

The skill uploads documents via Buy@ Assistant and includes them in the PR.

**Q: How do I check PR status?**
A: Ask Metamate:
- "Check status of PR-12345"
- "What's the status of my purchase request?"

You'll get current status, approver, approval chain, PO number (if approved), and any blockers.

**Q: Will I get notified when my PR is approved?**
A: Yes! If you use Direct Submission mode, the skill starts async monitoring and will notify you via:
- Metamate chat message
- Workplace post (if configured)
- Email (if configured)

Notifications are sent when: PR is submitted, approved, rejected, or status changes.

**Q: Can I update a PR after it's created?**
A: Yes, for draft PRs you can:
- Use the Buy@ UI to edit the draft directly
- Or ask Metamate: "Update PR-12345 to change quantity to 10"

For submitted PRs, updates may be limited depending on approval stage. The skill will inform you if changes are not possible.

**Q: How long does PR approval take?**
A: Approval time varies by:
- Amount (higher amounts require more approval levels)
- Category (some categories have specialized approvers)
- Approver availability

The skill shows you the approval chain so you know who needs to approve. Typical timelines:
- Under $10K: 1-2 business days
- $10K-$50K: 2-3 business days
- Over $50K: 3-5 business days (may require additional reviews)

## Troubleshooting Guide

### Vendor Onboarding Issues

**Issue: "Supplier not found in Buy@"**
- **Cause:** The supplier doesn't exist in Meta's Buy@ system
- **Solution:** 
  1. Verify the supplier's legal name (must match exactly)
  2. If it's a new supplier, the skill will guide you through inviting them
  3. Supplier will receive email from suppliers@fb.com with enrollment instructions
  4. Supplier has 10 business days to complete enrollment
  5. Once enrolled, you can proceed with onboarding

**Issue: "Supplier exists but is inactive"**
- **Cause:** Supplier was previously onboarded but is now inactive
- **Solution:**
  1. The skill will offer to reactivate the supplier via Buy@ Assistant
  2. Reactivation is faster than new onboarding (no 10-day enrollment)
  3. Follow the prompts to complete reactivation
  4. Once active, proceed with onboarding

**Issue: "TPA Assessment required" or "TPA expired"**
- **Cause:** Supplier needs security assessment or existing TPA has expired
- **Solution:**
  1. TPA is required for most suppliers handling Meta data
  2. The skill will initiate TPA via the TPA system
  3. TPA typically takes 3-5 business days
  4. You'll be notified when TPA is complete
  5. Onboarding will resume automatically after TPA approval

**Issue: "Worker email already exists"**
- **Cause:** A worker with that email is already in the system
- **Solution:**
  1. Verify the email address is correct
  2. Check if worker was previously onboarded
  3. If worker needs to be rehired, contact CSC support for reactivation
  4. Use a different email if it's a different person

**Issue: "Invalid cost center" or "Cost center not found"**
- **Cause:** The cost center provided doesn't exist or you don't have access
- **Solution:**
  1. Verify cost center format (e.g., CC-12345)
  2. Check with your manager or finance team for correct cost center
  3. Ensure you have permission to charge to that cost center
  4. Try using the Buy@ Assistant to search for valid cost centers

**Issue: "Spreadsheet validation failed"**
- **Cause:** Worker spreadsheet has formatting errors or missing required fields
- **Solution:**
  1. Download the template from the skill (it will provide a link)
  2. Ensure all required columns are present: Full Name, Email, Job Title, Start Date, End Date, Manager Email, Work Location
  3. Check date format: YYYY-MM-DD (e.g., 2026-07-01)
  4. Verify email addresses are valid format
  5. Ensure no empty rows in the spreadsheet
  6. Re-upload the corrected file

### Purchase Request Issues

**Issue: "Supplier not found in Buy@" when creating PR**
- **Cause:** Cannot create PR for supplier that doesn't exist in Buy@
- **Solution:**
  1. Verify supplier name spelling (must match Buy@ exactly)
  2. Use the skill to search for supplier: "Check if [Supplier] exists in Buy@"
  3. If supplier is new, onboard them first using the vendor onboarding workflow
  4. Once supplier is active in Buy@, create the PR

**Issue: "Supplier is not active" when creating PR**
- **Cause:** Supplier exists in Buy@ but status is inactive, pending, or suspended
- **Solution:**
  1. Check supplier status via Buy@ Assistant
  2. If inactive, reactivate the supplier first
  3. If pending, wait for supplier to complete enrollment
  4. Contact Buy@ support if status seems incorrect

**Issue: "TPA status is not active" or "TPA expired"**
- **Cause:** Supplier's Third Party Assessment is not current
- **Solution:**
  1. TPA must be active to create PRs for most suppliers
  2. Contact your security team to initiate TPA renewal
  3. TPA renewal typically takes 3-5 business days
  4. Once TPA is active, retry PR creation

**Issue: "PR creation failed" or "Buy@ Assistant error"**
- **Cause:** Temporary issue with Buy@ Assistant or network
- **Solution:**
  1. Wait a few minutes and try again
  2. The skill has automatic retry logic for transient failures
  3. If problem persists, check Buy@ status (is buy@ down?)
  4. Try creating PR manually via Buy@ UI as fallback
  5. Contact support with error details if issue continues

**Issue: "Document upload failed"**
- **Cause:** File may be too large, wrong format, or network issue
- **Solution:**
  1. Check file size (limit is typically 25MB per file)
  2. Verify file format: PDF, DOCX, XLSX, PNG, JPG are supported
  3. Ensure file is not corrupted (try opening it locally)
  4. Try uploading a different file to test
  5. If all uploads fail, you can create PR without attachments and add them manually later

**Issue: "PR status check failed" or "Cannot retrieve PR status"**
- **Cause:** PR number may be invalid, or Buy@ Assistant is temporarily unavailable
- **Solution:**
  1. Verify PR number format (should be like PR-12345)
  2. Check if PR exists by searching in Buy@ UI directly
  3. Wait a few minutes and try again (may be temporary)
  4. If PR was just created, wait 5-10 minutes for it to appear in system

**Issue: "Approval is taking too long"**
- **Cause:** Approver may be out of office, or PR requires additional reviews
- **Solution:**
  1. Check PR status to see current approver
  2. Contact the approver directly if urgent
  3. For PRs over $50K or $1M, additional compliance reviews may be required
  4. Ensure all required fields are complete (incomplete PRs may be delayed)
  5. Check if there are any blockers listed in PR status

**Issue: "PR was rejected"**
- **Cause:** Approver rejected the PR, typically due to missing information, incorrect amounts, or policy violations
- **Solution:**
  1. Check PR status for rejection reason
  2. Review the feedback from the approver
  3. Common reasons:
     - Insufficient business justification (use the AI justification tool to improve)
     - Incorrect cost center or funding
     - Missing required attachments (quotes, contracts)
     - Amount exceeds approval limit for category
  4. Update the PR with corrections (if still in draft) or create a new PR
  5. Address the specific feedback before resubmitting

### Technical Issues

**Issue: "Browser automation failed" or "Playwright error"**
- **Cause:** Issue with browser automation layer
- **Solution:**
  1. This is typically a transient issue - try again
  2. The skill has automatic retry logic
  3. If persistent, the Buy@ UI may have changed (requires code update)
  4. Contact the skill maintainers with error details

**Issue: "Metamate skill not responding"**
- **Cause:** Skill may be down or experiencing issues
- **Solution:**
  1. Try rephrasing your request
  2. Check if Metamate is experiencing broader issues
  3. Try again in a few minutes
  4. Use manual Buy@ UI as fallback for urgent requests
  5. Report issue to skill maintainers

**Issue: "Session timeout" or "Lost connection"**
- **Cause:** Long-running operation timed out
- **Solution:**
  1. For vendor onboarding, the skill supports checkpoint/resume
  2. Restart the skill and it should resume from where it left off
  3. For PR monitoring, the polling continues in background even if chat session ends
  4. Check PR status directly to see current state

## Getting Help

**For Skill Issues:**
- Contact: Igor Kosoy (ikosoy@meta.com)
- Team: BO&SS: Operations
- Oncall: RL Content Org Tools

**For Buy@ System Issues:**
- Buy@ Support: Visit buy@ help center or contact Buy@ support team
- Supplier Issues: suppliers@fb.com

**For CSC/Worker Issues:**
- CSC Support: Contact CSC help desk
- Access Issues: Contact your IT support team

**For TPA/Security Issues:**
- TPA Support: Contact your security team or TPA coordinators

**Documentation:**
- Skill Overview: `SKILL_OVERVIEW.md`
- Technical Details: `PR_IMPLEMENTATION_SUMMARY.md`
- Implementation Status: `PR_FEATURE_STATUS.md`
- User Guide: `docs/USER_GUIDE.md`

## Tips for Success

1. **Have information ready:** Before starting, gather supplier details, worker information, and PR requirements
2. **Use exact names:** Supplier names must match Buy@ exactly (case-sensitive)
3. **Validate early:** The skill validates in real-time - fix errors as they appear
4. **Save PR numbers:** Keep track of PR numbers for status checking later
5. **Monitor notifications:** Enable Workplace/Email notifications to stay updated
6. **Be specific:** Provide detailed descriptions and justifications for faster approval
7. **Attach documents:** Include quotes and SOWs to support your PR
8. **Check TPA early:** Verify supplier TPA status before starting PR to avoid delays
