"""CLI intake tool for vendor onboarding automation.

Provides interactive prompts for collecting all vendor onboarding data
in a single session, with validation, config file support, and dry-run mode.
"""

import json
import sys
import argparse
from typing import Any, Dict, List, Optional
from pathlib import Path
from getpass import getpass

from ..butterfly.client import ButterflyClient, ValidationError
from ..orchestrator.workflow import WorkflowOrchestrator


class IntakeCLI:
    """Interactive CLI for vendor onboarding intake."""
    
    def __init__(self, schema_path: str = "config/form_schemas.json"):
        """Initialize intake CLI.
        
        Args:
            schema_path: Path to form schemas configuration
        """
        self.schema_path = schema_path
        self.butterfly_client = ButterflyClient(schema_path)
        self.data: Dict[str, Any] = {}
    
    def _prompt(self, message: str, required: bool = True, default: Optional[str] = None) -> str:
        """Prompt user for input.
        
        Args:
            message: Prompt message
            required: Whether input is required
            default: Default value if user enters nothing
            
        Returns:
            User input string
        """
        prompt_msg = message
        if default:
            prompt_msg += f" [{default}]"
        prompt_msg += ": "
        
        while True:
            value = input(prompt_msg).strip()
            
            if not value and default:
                return default
            
            if not value and required:
                print("  This field is required. Please enter a value.")
                continue
            
            return value
    
    def _prompt_choice(self, message: str, choices: List[str], default: Optional[str] = None) -> str:
        """Prompt user to choose from a list of options.
        
        Args:
            message: Prompt message
            choices: List of valid choices
            default: Default choice
            
        Returns:
            Selected choice
        """
        print(f"\n{message}")
        for i, choice in enumerate(choices, 1):
            print(f"  {i}. {choice}")
        
        while True:
            prompt_msg = "Enter choice number"
            if default:
                default_idx = choices.index(default) + 1 if default in choices else None
                if default_idx:
                    prompt_msg += f" [{default_idx}]"
            prompt_msg += ": "
            
            value = input(prompt_msg).strip()
            
            if not value and default:
                return default
            
            try:
                idx = int(value) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]
                else:
                    print(f"  Please enter a number between 1 and {len(choices)}")
            except ValueError:
                print("  Please enter a valid number")
    
    def _prompt_yes_no(self, message: str, default: bool = True) -> bool:
        """Prompt user for yes/no answer.
        
        Args:
            message: Prompt message
            default: Default answer
            
        Returns:
            True for yes, False for no
        """
        default_str = "Y/n" if default else "y/N"
        prompt_msg = f"{message} [{default_str}]: "
        
        while True:
            value = input(prompt_msg).strip().lower()
            
            if not value:
                return default
            
            if value in ('y', 'yes'):
                return True
            elif value in ('n', 'no'):
                return False
            else:
                print("  Please enter 'y' or 'n'")
    
    def collect_supplier_info(self) -> Dict[str, Any]:
        """Collect supplier information."""
        print("\n" + "="*60)
        print("SUPPLIER INFORMATION")
        print("="*60)
        
        data = {}
        data['supplier_name'] = self._prompt("Supplier legal name")
        data['supplier_contact_email'] = self._prompt("Supplier contact email")
        data['supplier_contact_phone'] = self._prompt("Supplier contact phone (optional)", required=False)
        data['business_justification'] = self._prompt("Business justification")
        data['estimated_spend'] = self._prompt("Estimated annual spend (e.g., $100000)")
        data['contract_start_date'] = self._prompt("Contract start date (YYYY-MM-DD)")
        data['contract_end_date'] = self._prompt("Contract end date (YYYY-MM-DD)")
        data['requestor_manager'] = self._prompt("Requestor manager (unixname)")
        
        return data
    
    def collect_yubikey_info(self) -> Dict[str, Any]:
        """Collect YubiKey request information."""
        print("\n" + "="*60)
        print("YUBIKEY REQUEST")
        print("="*60)
        
        if not self._prompt_yes_no("Do vendor workers need YubiKeys?", default=True):
            return {}
        
        data = {}
        workers = []
        
        print("\nEnter vendor worker information (leave name empty to finish):")
        while True:
            name = self._prompt("Worker full name", required=False)
            if not name:
                break
            
            email = self._prompt(f"  Email for {name}")
            
            print(f"  Shipping address for {name}:")
            street = self._prompt("    Street address")
            city = self._prompt("    City")
            state = self._prompt("    State/Province")
            zip_code = self._prompt("    ZIP/Postal code")
            country = self._prompt("    Country")
            
            workers.append({
                "full_name": name,
                "email": email,
                "shipping_address": {
                    "street": street,
                    "city": city,
                    "state": state,
                    "zip": zip_code,
                    "country": country
                }
            })
        
        data['vendor_workers'] = workers
        data['urgency'] = self._prompt_choice(
            "Urgency level",
            ["Standard (3+ weeks)", "Expedited (1-2 weeks)", "Emergency (< 1 week)"],
            default="Standard (3+ weeks)"
        )
        data['business_justification'] = self._prompt("Business justification for YubiKeys")
        
        return data
    
    def collect_sow_info(self) -> Dict[str, Any]:
        """Collect Statement of Work information."""
        print("\n" + "="*60)
        print("STATEMENT OF WORK")
        print("="*60)
        
        data = {}
        data['vendor_name'] = self.data.get('supplier_name', self._prompt("Vendor name"))
        data['sow_title'] = self._prompt("SOW title")
        data['scope_description'] = self._prompt("Scope description (detailed)")
        
        # Collect deliverables
        deliverables = []
        print("\nEnter deliverables (leave name empty to finish):")
        while True:
            name = self._prompt("Deliverable name", required=False)
            if not name:
                break
            
            description = self._prompt(f"  Description for {name}")
            due_date = self._prompt(f"  Due date for {name} (YYYY-MM-DD)")
            
            deliverables.append({
                "name": name,
                "description": description,
                "due_date": due_date
            })
        
        data['deliverables'] = deliverables
        data['start_date'] = self._prompt("SOW start date (YYYY-MM-DD)")
        data['end_date'] = self._prompt("SOW end date (YYYY-MM-DD)")
        data['total_value'] = self._prompt("Total SOW value (e.g., $50000)")
        data['payment_terms'] = self._prompt_choice(
            "Payment terms",
            ["Net 30", "Net 45", "Net 60", "Milestone-based"],
            default="Net 30"
        )
        
        return data
    
    def collect_csc_info(self) -> Dict[str, Any]:
        """Collect CSC program setup information."""
        print("\n" + "="*60)
        print("CSC PROGRAM SETUP")
        print("="*60)
        
        data = {}
        data['program_name'] = self._prompt("Program name")
        data['vendor_name'] = self.data.get('supplier_name', self._prompt("Vendor name"))
        data['program_manager'] = self._prompt("Meta program manager (unixname)")
        
        print("\nVendor manager information:")
        vendor_manager = {
            "name": self._prompt("  Name"),
            "email": self._prompt("  Email"),
            "phone": self._prompt("  Phone (optional)", required=False)
        }
        data['vendor_manager'] = vendor_manager
        
        data['worker_count'] = int(self._prompt("Number of vendor workers"))
        data['work_location'] = self._prompt_choice(
            "Work location",
            ["Onsite", "Remote", "Hybrid"],
            default="Remote"
        )
        
        if data['work_location'] in ["Onsite", "Hybrid"]:
            data['office_location'] = self._prompt("Meta office location")
        
        data['start_date'] = self._prompt("Program start date (YYYY-MM-DD)")
        
        # Access requirements
        print("\nEnter systems/tools vendor needs access to (leave empty to finish):")
        access_reqs = []
        while True:
            system = self._prompt("System/tool name", required=False)
            if not system:
                break
            access_reqs.append(system)
        data['access_requirements'] = access_reqs
        
        data['amp_group_name'] = self._prompt("AMP group name for access management")
        
        return data
    
    def collect_tpa_info(self) -> Dict[str, Any]:
        """Collect TPA assessment information."""
        print("\n" + "="*60)
        print("THIRD PARTY ASSESSMENT (TPA)")
        print("="*60)
        
        data = {}
        
        # Supplier information
        print("\nSupplier Information:")
        supplier_info = {
            "legal_name": self.data.get('supplier_name', self._prompt("  Legal name")),
            "dba_name": self._prompt("  DBA name (optional)", required=False),
            "website": self._prompt("  Website (optional)", required=False)
        }
        
        print("  Primary contact:")
        supplier_info["primary_contact"] = {
            "name": self._prompt("    Name"),
            "title": self._prompt("    Title"),
            "email": self._prompt("    Email"),
            "phone": self._prompt("    Phone")
        }
        data['supplier_information'] = supplier_info
        
        # Business information
        print("\nBusiness Information:")
        business_info = {
            "business_justification": self.data.get('business_justification', self._prompt("  Business justification")),
            "estimated_annual_spend": self.data.get('estimated_spend', self._prompt("  Estimated annual spend")),
            "contract_duration_months": int(self._prompt("  Contract duration (months)"))
        }
        data['business_information'] = business_info
        
        # TPA assessment
        print("\nTPA Assessment:")
        tpa_assessment = {
            "data_access_level": self._prompt_choice(
                "  Data access level",
                ["Public", "Internal", "Confidential", "Highly Confidential"],
                default="Internal"
            ),
            "systems_access": data.get('access_requirements', []),
            "handles_pii": self._prompt_yes_no("  Will vendor handle PII?", default=False),
            "handles_financial_data": self._prompt_yes_no("  Will vendor handle financial data?", default=False),
            "security_questionnaire_completed": self._prompt_yes_no("  Has security questionnaire been completed?", default=False)
        }
        data['tpa_assessment'] = tpa_assessment
        
        return data
    
    def run_interactive(self) -> Dict[str, Any]:
        """Run interactive intake session.
        
        Returns:
            Collected data dictionary
        """
        print("\n" + "="*60)
        print("VENDOR ONBOARDING AUTOMATION - INTAKE")
        print("="*60)
        print("\nThis tool will collect all information needed for vendor onboarding.")
        print("You can save your progress and resume later.")
        
        # Collect all sections
        self.data['supplier'] = self.collect_supplier_info()
        self.data['yubikey'] = self.collect_yubikey_info()
        self.data['sow'] = self.collect_sow_info()
        self.data['csc'] = self.collect_csc_info()
        self.data['tpa'] = self.collect_tpa_info()
        
        print("\n" + "="*60)
        print("INTAKE COMPLETE")
        print("="*60)
        print(f"\nCollected data for {len(self.data)} sections.")
        
        return self.data
    
    def load_from_file(self, filepath: str) -> Dict[str, Any]:
        """Load intake data from JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Loaded data dictionary
        """
        with open(filepath, 'r') as f:
            self.data = json.load(f)
        print(f"Loaded intake data from {filepath}")
        return self.data
    
    def save_to_file(self, filepath: str) -> None:
        """Save intake data to JSON file.
        
        Args:
            filepath: Path to output JSON file
        """
        with open(filepath, 'w') as f:
            json.dump(self.data, f, indent=2)
        print(f"Saved intake data to {filepath}")
    
    def validate(self) -> List[str]:
        """Validate collected data against form schemas.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate each section against its form schema
        if 'supplier' in self.data:
            errs = self.butterfly_client.validate_form_data(
                'supplier_onboarding_request',
                self.data['supplier']
            )
            errors.extend([f"Supplier: {e}" for e in errs])
        
        if 'yubikey' in self.data and self.data['yubikey']:
            errs = self.butterfly_client.validate_form_data(
                'yubikey_request',
                self.data['yubikey']
            )
            errors.extend([f"YubiKey: {e}" for e in errs])
        
        if 'sow' in self.data:
            errs = self.butterfly_client.validate_form_data(
                'statement_of_work',
                self.data['sow']
            )
            errors.extend([f"SOW: {e}" for e in errs])
        
        if 'csc' in self.data:
            errs = self.butterfly_client.validate_form_data(
                'csc_new_outsourced_program',
                self.data['csc']
            )
            errors.extend([f"CSC: {e}" for e in errs])
        
        if 'tpa' in self.data:
            errs = self.butterfly_client.validate_form_data(
                'combined_supplier_onboarding_tpa',
                self.data['tpa']
            )
            errors.extend([f"TPA: {e}" for e in errs])
        
        return errors


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Vendor Onboarding Automation - Intake CLI"
    )
    parser.add_argument(
        '--config', '-c',
        help='Load intake data from JSON config file'
    )
    parser.add_argument(
        '--output', '-o',
        help='Save intake data to JSON file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate data without submitting forms'
    )
    parser.add_argument(
        '--schema',
        default='config/form_schemas.json',
        help='Path to form schemas configuration'
    )
    
    args = parser.parse_args()
    
    cli = IntakeCLI(schema_path=args.schema)
    
    # Load from file or run interactive
    if args.config:
        cli.load_from_file(args.config)
    else:
        cli.run_interactive()
    
    # Validate data
    print("\nValidating intake data...")
    errors = cli.validate()
    
    if errors:
        print("\nValidation errors found:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("Validation passed!")
    
    # Save to file if requested
    if args.output:
        cli.save_to_file(args.output)
    
    if args.dry_run:
        print("\nDry run complete. No forms were submitted.")
        return
    
    # TODO: Submit forms via workflow orchestrator
    print("\nReady to submit forms. Use the workflow orchestrator to execute.")


if __name__ == '__main__':
    main()
