# Kumar Brothers Steel ERP

A comprehensive ERPNext customization for the steel fabrication industry, designed specifically for Kumar Brothers Steel operations.

## Features

### Core Modules

1. **Steel Inventory Management**
   - Raw material tracking (pipes, plates, beams, angles, channels)
   - Grade and specification management
   - Heat number tracking for quality control
   - Real-time stock levels with warehouse locations

2. **Material Tracking System**
   - Unique tracking codes for each material batch
   - Full traceability from receipt to dispatch
   - Customer-specific tracking
   - Barcode/QR code support

3. **Goods Receipt Notes (GRN)**
   - Supplier delivery recording
   - Quality inspection integration
   - Weight verification (mill weight vs actual weight)
   - Automatic inventory updates

4. **Dispatch Management**
   - Delivery challan generation
   - Vehicle and transporter tracking
   - Loading slip generation
   - Customer delivery confirmation

5. **Customer Management**
   - Customer-specific pricing
   - Credit limit management
   - Outstanding balance tracking
   - Delivery address management

6. **Cutting Instructions**
   - Job work order management
   - Cutting specifications
   - Wastage tracking
   - Cost calculation

### Steel-Specific Fields

- **Material Grade**: IS2062 E250, E350, etc.
- **Dimensions**: Length, Width, Thickness, Diameter
- **Weight Calculation**: Per piece and total weight
- **Heat Number**: Mill certificate tracking
- **Surface Finish**: Galvanized, Painted, Mill finish

## Installation

1. Install ERPNext v15
2. Get the steel_erp app:
   ```bash
   bench get-app steel_erp
   ```
3. Install on your site:
   ```bash
   bench --site your-site install-app steel_erp
   ```

## Configuration

After installation, run the setup wizard to configure:
- Company details
- Warehouses (Main Store, Cutting Area, Dispatch Bay)
- Item Groups for steel products
- UOMs (MT, KG, Nos, Mtr, Feet)
- Tax templates for GST

## Support

Contact: admin@kumarbrothers.com
