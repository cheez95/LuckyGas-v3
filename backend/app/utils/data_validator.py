"""
Data validation framework for Lucky Gas migration
Validates data integrity, business rules, and Taiwan-specific formats
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple, Set
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from collections import defaultdict

from app.models import Customer, Order, User, Vehicle, GasProduct
from app.models.order import OrderStatus
from app.models.user import UserRole

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Comprehensive data validation for Lucky Gas migration.
    Validates formats, business rules, and data integrity.
    """

    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []
        self.validation_stats = {
            "total_records": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "warnings": 0,
            "errors_by_type": defaultdict(int),
            "warnings_by_type": defaultdict(int),
        }

    def reset_stats(self):
        """Reset validation statistics and errors."""
        self.validation_errors = []
        self.validation_warnings = []
        self.validation_stats = {
            "total_records": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "warnings": 0,
            "errors_by_type": defaultdict(int),
            "warnings_by_type": defaultdict(int),
        }

    # Taiwan-specific format validators

    @staticmethod
    def validate_taiwan_phone(phone: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Taiwan phone number format.

        Returns:
            (is_valid, normalized_phone)
        """
        if not phone:
            return False, None

        # Remove common separators
        cleaned = re.sub(r"[\s\-\(\)]", "", str(phone))

        # Mobile: 09XX followed by 6 digits
        mobile_pattern = r"^09\d{8}$"
        # Landline: 0 + area code (1-2 digits) + 7-8 digits
        landline_pattern = r"^0[2-8]\d{7,8}$"

        if re.match(mobile_pattern, cleaned):
            # Format as 09XX-XXX-XXX
            return True, f"{cleaned[:4]}-{cleaned[4:7]}-{cleaned[7:]}"
        elif re.match(landline_pattern, cleaned):
            # Format based on area code length
            if cleaned[0:2] in ["02", "03", "04", "05", "06", "07", "08"]:
                # 2-digit area code
                return True, f"{cleaned[:2]}-{cleaned[2:6]}-{cleaned[6:]}"
            else:
                # 3-digit area code
                return True, f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"

        return False, None

    @staticmethod
    def validate_taiwan_address(address: str) -> Tuple[bool, List[str]]:
        """
        Validate Taiwan address format and extract components.

        Returns:
            (is_valid, [issues])
        """
        if not address:
            return False, ["Address is empty"]

        issues = []

        # Check for required components
        required_patterns = {
            "縣市": r"(台北市|新北市|桃園市|台中市|台南市|高雄市|基隆市|新竹市|嘉義市|新竹縣|苗栗縣|彰化縣|南投縣|雲林縣|嘉義縣|屏東縣|宜蘭縣|花蓮縣|台東縣|澎湖縣|金門縣|連江縣)",
            "區鄉鎮": r"(區|鄉|鎮|市)",
            "路街": r"(路|街|巷|弄|段)",
            "號": r"號",
        }

        for component, pattern in required_patterns.items():
            if not re.search(pattern, address):
                issues.append(f"Missing {component} in address")

        # Check for postal code (optional but recommended)
        postal_pattern = r"^\d{3,5}"
        if not re.match(postal_pattern, address):
            issues.append("No postal code at beginning of address")

        # Check for common typos or issues
        if "台灣" in address and "台灣省" not in address:
            issues.append("Contains '台灣' - might be redundant")

        return len(issues) == 0, issues

    @staticmethod
    def validate_taiwan_tax_id(tax_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Taiwan business tax ID (統一編號).

        Returns:
            (is_valid, formatted_tax_id)
        """
        if not tax_id:
            return True, None  # Optional field

        # Remove any formatting
        cleaned = re.sub(r"\D", "", str(tax_id))

        # Must be exactly 8 digits
        if len(cleaned) != 8:
            return False, None

        # Taiwan tax ID checksum validation
        weights = [1, 2, 1, 2, 1, 2, 4, 1]
        checksum = 0

        for i, digit in enumerate(cleaned):
            product = int(digit) * weights[i]
            checksum += product // 10 + product % 10

        is_valid = checksum % 10 == 0
        return is_valid, cleaned if is_valid else None

    # Data type validators

    def validate_customer_data(self, customer_df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate customer data from legacy system.

        Returns:
            DataFrame with validation results
        """
        self.reset_stats()
        self.validation_stats["total_records"] = len(customer_df)

        # Add validation columns
        customer_df["is_valid"] = True
        customer_df["validation_errors"] = ""
        customer_df["validation_warnings"] = ""

        for idx, row in customer_df.iterrows():
            errors = []
            warnings = []

            # Required fields
            if pd.isna(row.get("client_code")) or not str(row["client_code"]).strip():
                errors.append("Missing client_code")
                self.validation_stats["errors_by_type"]["missing_client_code"] += 1

            if pd.isna(row.get("address")) or not str(row["address"]).strip():
                errors.append("Missing address")
                self.validation_stats["errors_by_type"]["missing_address"] += 1

            # Validate phone
            phone = row.get("phone") or row.get("contact_person", "")
            if phone:
                phone_valid, normalized = self.validate_taiwan_phone(phone)
                if not phone_valid:
                    warnings.append(f"Invalid phone format: {phone}")
                    self.validation_stats["warnings_by_type"]["invalid_phone"] += 1

            # Validate address
            if row.get("address"):
                addr_valid, addr_issues = self.validate_taiwan_address(
                    str(row["address"])
                )
                if not addr_valid:
                    warnings.extend(addr_issues)
                    self.validation_stats["warnings_by_type"]["address_issues"] += 1

            # Validate tax ID
            if row.get("tax_id"):
                tax_valid, _ = self.validate_taiwan_tax_id(str(row["tax_id"]))
                if not tax_valid:
                    warnings.append(f"Invalid tax ID: {row['tax_id']}")
                    self.validation_stats["warnings_by_type"]["invalid_tax_id"] += 1

            # Business rule validations

            # Check coordinates
            if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
                lat = float(row["latitude"])
                lng = float(row["longitude"])

                # Taiwan bounds approximately
                if not (21.5 <= lat <= 26 and 119 <= lng <= 122.5):
                    warnings.append(f"Coordinates outside Taiwan: {lat}, {lng}")
                    self.validation_stats["warnings_by_type"][
                        "invalid_coordinates"
                    ] += 1

            # Check cylinder inventory
            cylinder_cols = [
                "cylinder_50kg",
                "cylinder_20kg",
                "cylinder_16kg",
                "cylinder_10kg",
                "cylinder_4kg",
            ]
            for col in cylinder_cols:
                if pd.notna(row.get(col)):
                    try:
                        value = int(row[col])
                        if value < 0:
                            errors.append(f"Negative {col}: {value}")
                            self.validation_stats["errors_by_type"][
                                "negative_inventory"
                            ] += 1
                        elif value > 1000:
                            warnings.append(f"Unusually high {col}: {value}")
                            self.validation_stats["warnings_by_type"][
                                "high_inventory"
                            ] += 1
                    except:
                        errors.append(f"Invalid number for {col}: {row[col]}")
                        self.validation_stats["errors_by_type"]["invalid_number"] += 1

            # Check delivery time preferences
            if row.get("needs_same_day_delivery") and not any(
                row.get(f"hour_{h}_{h+1}") for h in range(8, 20)
            ):
                warnings.append(
                    "Same-day delivery requested but no time slots selected"
                )
                self.validation_stats["warnings_by_type"]["missing_time_slots"] += 1

            # Update row
            customer_df.at[idx, "is_valid"] = len(errors) == 0
            customer_df.at[idx, "validation_errors"] = "; ".join(errors)
            customer_df.at[idx, "validation_warnings"] = "; ".join(warnings)

            if errors:
                self.validation_errors.append(
                    {"record": row["client_code"], "errors": errors}
                )
                self.validation_stats["invalid_records"] += 1
            else:
                self.validation_stats["valid_records"] += 1

            if warnings:
                self.validation_warnings.append(
                    {"record": row["client_code"], "warnings": warnings}
                )
                self.validation_stats["warnings"] += 1

        return customer_df

    def validate_order_data(self, order_df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate order/delivery data.

        Returns:
            DataFrame with validation results
        """
        self.reset_stats()
        self.validation_stats["total_records"] = len(order_df)

        # Add validation columns
        order_df["is_valid"] = True
        order_df["validation_errors"] = ""
        order_df["validation_warnings"] = ""

        for idx, row in order_df.iterrows():
            errors = []
            warnings = []

            # Required fields
            if pd.isna(row.get("client_id")):
                errors.append("Missing client_id")
                self.validation_stats["errors_by_type"]["missing_client_id"] += 1

            if pd.isna(row.get("scheduled_date")):
                errors.append("Missing scheduled_date")
                self.validation_stats["errors_by_type"]["missing_date"] += 1
            else:
                # Validate date
                try:
                    sched_date = pd.to_datetime(row["scheduled_date"]).date()

                    # Check if date is reasonable (not too far in past or future)
                    today = date.today()
                    days_diff = (today - sched_date).days

                    if days_diff > 365 * 5:  # More than 5 years old
                        warnings.append(f"Very old order: {sched_date}")
                        self.validation_stats["warnings_by_type"]["old_order"] += 1
                    elif days_diff < -365:  # More than 1 year in future
                        warnings.append(f"Far future order: {sched_date}")
                        self.validation_stats["warnings_by_type"]["future_order"] += 1
                except:
                    errors.append(f"Invalid date format: {row['scheduled_date']}")
                    self.validation_stats["errors_by_type"]["invalid_date"] += 1

            # Validate status
            if row.get("status"):
                valid_statuses = [
                    "pending",
                    "confirmed",
                    "in_delivery",
                    "delivered",
                    "cancelled",
                    "failed",
                ]
                if str(row["status"]).lower() not in valid_statuses:
                    errors.append(f"Invalid status: {row['status']}")
                    self.validation_stats["errors_by_type"]["invalid_status"] += 1

            # Validate quantities
            delivered_cols = [
                "delivered_50kg",
                "delivered_20kg",
                "delivered_16kg",
                "delivered_10kg",
                "delivered_4kg",
            ]
            returned_cols = [
                "returned_50kg",
                "returned_20kg",
                "returned_16kg",
                "returned_10kg",
                "returned_4kg",
            ]

            total_delivered = 0
            for col in delivered_cols:
                if pd.notna(row.get(col)):
                    try:
                        value = int(row[col])
                        if value < 0:
                            errors.append(f"Negative {col}: {value}")
                            self.validation_stats["errors_by_type"][
                                "negative_quantity"
                            ] += 1
                        total_delivered += value
                    except:
                        errors.append(f"Invalid number for {col}: {row[col]}")
                        self.validation_stats["errors_by_type"]["invalid_number"] += 1

            # Check returned vs delivered
            for i, (del_col, ret_col) in enumerate(zip(delivered_cols, returned_cols)):
                if pd.notna(row.get(ret_col)) and pd.notna(row.get(del_col)):
                    try:
                        returned = int(row[ret_col])
                        delivered = int(row[del_col])
                        if returned > delivered:
                            warnings.append(f"Returned > delivered for {ret_col}")
                            self.validation_stats["warnings_by_type"][
                                "return_exceed"
                            ] += 1
                    except:
                        pass

            # Check if any items delivered
            if total_delivered == 0 and str(row.get("status")).lower() == "delivered":
                warnings.append("Status is delivered but no items delivered")
                self.validation_stats["warnings_by_type"]["no_items_delivered"] += 1

            # Validate delivery confirmation
            if str(row.get("status")).lower() == "delivered":
                if pd.isna(row.get("actual_delivery_time")):
                    warnings.append("Delivered but no actual_delivery_time")
                    self.validation_stats["warnings_by_type"][
                        "missing_delivery_time"
                    ] += 1

            # Update row
            order_df.at[idx, "is_valid"] = len(errors) == 0
            order_df.at[idx, "validation_errors"] = "; ".join(errors)
            order_df.at[idx, "validation_warnings"] = "; ".join(warnings)

            if errors:
                self.validation_errors.append(
                    {"record": f"order_{row.get('id', idx)}", "errors": errors}
                )
                self.validation_stats["invalid_records"] += 1
            else:
                self.validation_stats["valid_records"] += 1

            if warnings:
                self.validation_warnings.append(
                    {"record": f"order_{row.get('id', idx)}", "warnings": warnings}
                )
                self.validation_stats["warnings"] += 1

        return order_df

    async def validate_referential_integrity(
        self, session: AsyncSession, customer_df: pd.DataFrame, order_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Validate referential integrity between tables.

        Returns:
            Dictionary with integrity check results
        """
        integrity_issues = {
            "orphaned_orders": [],
            "invalid_drivers": [],
            "invalid_vehicles": [],
            "duplicate_customers": [],
            "duplicate_orders": [],
        }

        # Check for orphaned orders (orders without valid customers)
        customer_ids = set(customer_df["id"].unique())
        for _, order in order_df.iterrows():
            if order["client_id"] not in customer_ids:
                integrity_issues["orphaned_orders"].append(
                    {
                        "order_id": order["id"],
                        "client_id": order["client_id"],
                        "scheduled_date": order["scheduled_date"],
                    }
                )

        # Check for duplicate customer codes
        customer_codes = customer_df["client_code"].value_counts()
        duplicates = customer_codes[customer_codes > 1]
        for code, count in duplicates.items():
            integrity_issues["duplicate_customers"].append(
                {"client_code": code, "count": count}
            )

        # Check driver references
        if "driver_id" in order_df.columns:
            driver_ids = order_df["driver_id"].dropna().unique()
            if len(driver_ids) > 0:
                # Verify drivers exist (would need driver data)
                pass

        # Summary
        summary = {
            "total_customers": len(customer_df),
            "total_orders": len(order_df),
            "orphaned_orders": len(integrity_issues["orphaned_orders"]),
            "duplicate_customers": len(integrity_issues["duplicate_customers"]),
            "issues": integrity_issues,
        }

        return summary

    def generate_validation_report(self) -> str:
        """
        Generate a comprehensive validation report.

        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append("Lucky Gas Data Validation Report")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now()}")
        report.append("")

        # Summary statistics
        report.append("SUMMARY STATISTICS")
        report.append("-" * 40)
        report.append(f"Total Records: {self.validation_stats['total_records']}")
        report.append(f"Valid Records: {self.validation_stats['valid_records']}")
        report.append(f"Invalid Records: {self.validation_stats['invalid_records']}")
        report.append(f"Records with Warnings: {self.validation_stats['warnings']}")

        if self.validation_stats["total_records"] > 0:
            validity_rate = (
                self.validation_stats["valid_records"]
                / self.validation_stats["total_records"]
                * 100
            )
            report.append(f"Validity Rate: {validity_rate:.2f}%")
        report.append("")

        # Error breakdown
        if self.validation_stats["errors_by_type"]:
            report.append("ERROR BREAKDOWN")
            report.append("-" * 40)
            for error_type, count in sorted(
                self.validation_stats["errors_by_type"].items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                report.append(f"{error_type}: {count}")
            report.append("")

        # Warning breakdown
        if self.validation_stats["warnings_by_type"]:
            report.append("WARNING BREAKDOWN")
            report.append("-" * 40)
            for warning_type, count in sorted(
                self.validation_stats["warnings_by_type"].items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                report.append(f"{warning_type}: {count}")
            report.append("")

        # Sample errors
        if self.validation_errors:
            report.append("SAMPLE ERRORS (First 10)")
            report.append("-" * 40)
            for error in self.validation_errors[:10]:
                report.append(f"Record: {error['record']}")
                for err in error["errors"]:
                    report.append(f"  - {err}")
            report.append("")

        # Sample warnings
        if self.validation_warnings:
            report.append("SAMPLE WARNINGS (First 10)")
            report.append("-" * 40)
            for warning in self.validation_warnings[:10]:
                report.append(f"Record: {warning['record']}")
                for warn in warning["warnings"]:
                    report.append(f"  - {warn}")
            report.append("")

        return "\n".join(report)

    def export_validation_results(self, output_path: str, include_details: bool = True):
        """
        Export validation results to file.

        Args:
            output_path: Path to save report
            include_details: Include detailed error/warning lists
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.generate_validation_report())

            if include_details and (self.validation_errors or self.validation_warnings):
                f.write("\n\n")
                f.write("=" * 80)
                f.write("\nDETAILED VALIDATION RESULTS\n")
                f.write("=" * 80)

                if self.validation_errors:
                    f.write("\n\nALL ERRORS\n")
                    f.write("-" * 40)
                    for i, error in enumerate(self.validation_errors, 1):
                        f.write(f"\n{i}. Record: {error['record']}\n")
                        for err in error["errors"]:
                            f.write(f"   - {err}\n")

                if self.validation_warnings:
                    f.write("\n\nALL WARNINGS\n")
                    f.write("-" * 40)
                    for i, warning in enumerate(self.validation_warnings, 1):
                        f.write(f"\n{i}. Record: {warning['record']}\n")
                        for warn in warning["warnings"]:
                            f.write(f"   - {warn}\n")


# Utility functions for specific validation tasks


def validate_migration_data(
    customer_df: pd.DataFrame,
    order_df: pd.DataFrame,
    output_dir: str = "validation_results",
) -> Dict[str, Any]:
    """
    Run complete validation on migration data.

    Returns:
        Dictionary with validation results
    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    validator = DataValidator()

    # Validate customers
    logger.info("Validating customer data...")
    validated_customers = validator.validate_customer_data(customer_df)
    validated_customers.to_csv(
        os.path.join(output_dir, "validated_customers.csv"), index=False
    )

    customer_report = validator.generate_validation_report()
    with open(os.path.join(output_dir, "customer_validation_report.txt"), "w") as f:
        f.write(customer_report)

    customer_stats = validator.validation_stats.copy()

    # Validate orders
    logger.info("Validating order data...")
    validator.reset_stats()
    validated_orders = validator.validate_order_data(order_df)
    validated_orders.to_csv(
        os.path.join(output_dir, "validated_orders.csv"), index=False
    )

    order_report = validator.generate_validation_report()
    with open(os.path.join(output_dir, "order_validation_report.txt"), "w") as f:
        f.write(order_report)

    order_stats = validator.validation_stats.copy()

    # Combined summary
    summary = {
        "customer_validation": customer_stats,
        "order_validation": order_stats,
        "total_customers": len(customer_df),
        "valid_customers": customer_stats["valid_records"],
        "total_orders": len(order_df),
        "valid_orders": order_stats["valid_records"],
        "overall_validity_rate": (
            (customer_stats["valid_records"] + order_stats["valid_records"])
            / (customer_stats["total_records"] + order_stats["total_records"])
            * 100
        ),
    }

    # Save summary
    import json

    with open(os.path.join(output_dir, "validation_summary.json"), "w") as f:
        json.dumps(summary, f, indent=2, default=str)

    logger.info(f"Validation complete. Results saved to {output_dir}")
    logger.info(f"Overall validity rate: {summary['overall_validity_rate']:.2f}%")

    return summary


if __name__ == "__main__":
    # Example usage
    import sys
    import sqlite3

    if len(sys.argv) < 2:
        print("Usage: python data_validator.py <legacy_db_path> [output_dir]")
        sys.exit(1)

    db_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "validation_results"

    # Load data
    conn = sqlite3.connect(db_path)
    customers_df = pd.read_sql_query("SELECT * FROM clients", conn)
    orders_df = pd.read_sql_query("SELECT * FROM deliveries", conn)
    conn.close()

    # Run validation
    results = validate_migration_data(customers_df, orders_df, output_dir)

    print(f"\nValidation Summary:")
    print(
        f"  Valid Customers: {results['valid_customers']}/{results['total_customers']}"
    )
    print(f"  Valid Orders: {results['valid_orders']}/{results['total_orders']}")
    print(f"  Overall Validity: {results['overall_validity_rate']:.2f}%")
