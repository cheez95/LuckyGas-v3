"""
Product import/export endpoints for Excel files
"""
from typing import Any
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import pandas as pd
import io
from datetime import datetime

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.gas_product import GasProduct as GasProductModel
from app.models.gas_product import DeliveryMethod, ProductAttribute
from app.models.user import User as UserModel
from app.models.user import UserRole
from app.schemas.gas_product import GasProductCreate

router = APIRouter()


@router.post("/import")
def import_products(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Import products from Excel file
    Requires manager or super_admin role
    """
    # Check permissions
    allowed_roles = [UserRole.MANAGER, UserRole.SUPER_ADMIN, "manager", "super_admin"]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")

    try:
        # Read Excel file
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # Required columns
        required_columns = [
            '配送方式', '規格', '屬性', '中文名稱', '單價'
        ]
        
        # Check for required columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )

        imported_count = 0
        skipped_count = 0
        errors = []

        # Process each row
        for index, row in df.iterrows():
            try:
                # Map delivery method
                delivery_method_map = {
                    'CYLINDER': DeliveryMethod.CYLINDER,
                    '桶裝': DeliveryMethod.CYLINDER,
                    'FLOW': DeliveryMethod.FLOW,
                    '流量': DeliveryMethod.FLOW,
                }
                delivery_method = delivery_method_map.get(
                    str(row['配送方式']).upper(),
                    DeliveryMethod.CYLINDER
                )

                # Map attribute
                attribute_map = {
                    'REGULAR': ProductAttribute.REGULAR,
                    '一般': ProductAttribute.REGULAR,
                    'COMMERCIAL': ProductAttribute.COMMERCIAL,
                    '營業用': ProductAttribute.COMMERCIAL,
                    'HAOYUN': ProductAttribute.HAOYUN,
                    '好運': ProductAttribute.HAOYUN,
                    'PINGAN': ProductAttribute.PINGAN,
                    '瓶安': ProductAttribute.PINGAN,
                    'XINGFU': ProductAttribute.XINGFU,
                    '幸福': ProductAttribute.XINGFU,
                    'SPECIAL': ProductAttribute.SPECIAL,
                    '特殊': ProductAttribute.SPECIAL,
                }
                attribute = attribute_map.get(
                    str(row.get('屬性', 'REGULAR')).upper(),
                    ProductAttribute.REGULAR
                )

                # Parse size
                size_kg = int(row['規格']) if pd.notna(row['規格']) else 20

                # Generate SKU if not provided
                sku = row.get('產品編號')
                if pd.isna(sku) or not sku:
                    method_prefix = 'F' if delivery_method == DeliveryMethod.FLOW else 'C'
                    attr_suffix = attribute.value[:3].upper()
                    sku = f"{method_prefix}-{size_kg}KG-{attr_suffix}"

                # Check if product already exists
                existing_product = db.query(GasProductModel).filter(
                    GasProductModel.delivery_method == delivery_method,
                    GasProductModel.size_kg == size_kg,
                    GasProductModel.attribute == attribute
                ).first()

                if existing_product:
                    # Update existing product
                    existing_product.name_zh = str(row['中文名稱'])
                    existing_product.unit_price = float(row['單價'])
                    if pd.notna(row.get('押金')):
                        existing_product.deposit_amount = float(row['押金'])
                    if pd.notna(row.get('英文名稱')):
                        existing_product.name_en = str(row['英文名稱'])
                    if pd.notna(row.get('描述')):
                        existing_product.description = str(row['描述'])
                    
                    skipped_count += 1
                else:
                    # Create new product
                    new_product = GasProductModel(
                        delivery_method=delivery_method,
                        size_kg=size_kg,
                        attribute=attribute,
                        sku=sku,
                        name_zh=str(row['中文名稱']),
                        name_en=str(row.get('英文名稱', '')) if pd.notna(row.get('英文名稱')) else None,
                        description=str(row.get('描述', '')) if pd.notna(row.get('描述')) else None,
                        unit_price=float(row['單價']),
                        deposit_amount=float(row.get('押金', 0)) if pd.notna(row.get('押金')) else 0,
                        is_active=bool(row.get('啟用', True)) if pd.notna(row.get('啟用')) else True,
                        is_available=bool(row.get('可訂購', True)) if pd.notna(row.get('可訂購')) else True,
                        track_inventory=bool(row.get('追蹤庫存', True)) if pd.notna(row.get('追蹤庫存')) else True,
                        low_stock_threshold=int(row.get('低庫存警示', 10)) if pd.notna(row.get('低庫存警示')) else 10,
                    )
                    db.add(new_product)
                    imported_count += 1

            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                continue

        # Commit changes
        db.commit()

        return {
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "errors": errors[:10],  # Return only first 10 errors
            "message": f"成功匯入 {imported_count} 個產品，跳過 {skipped_count} 個已存在的產品"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/export")
def export_products(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Export all products to Excel file
    """
    try:
        # Fetch all products
        products = db.query(GasProductModel).order_by(
            GasProductModel.delivery_method,
            GasProductModel.size_kg,
            GasProductModel.attribute
        ).all()

        # Convert to DataFrame
        data = []
        for product in products:
            data.append({
                '產品編號': product.sku,
                '配送方式': product.delivery_method.value,
                '規格': product.size_kg,
                '屬性': product.attribute.value,
                '中文名稱': product.name_zh,
                '英文名稱': product.name_en or '',
                '描述': product.description or '',
                '單價': product.unit_price,
                '押金': product.deposit_amount,
                '啟用': product.is_active,
                '可訂購': product.is_available,
                '追蹤庫存': product.track_inventory,
                '低庫存警示': product.low_stock_threshold,
                '顯示名稱': product.display_name,
            })

        df = pd.DataFrame(data)

        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Products')
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Products']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)

        # Return as streaming response
        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename=products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")