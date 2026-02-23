# Kumar Brothers Steel Fabrication ERP 🏭

<p align="center">
  <strong>Complete Manufacturing, Inventory & Scrap Management System for Steel Industry</strong>
</p>

![Kumar Brothers Steel ERP](https://img.shields.io/badge/Kumar%20Brothers-Steel%20ERP-blue?style=for-the-badge)
![Laravel](https://img.shields.io/badge/Laravel-12.x-red?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

## 🎯 Why Kumar Brothers Steel ERP?

Designed **specifically for steel fabrication industry**, this ERP addresses the unique challenges of steel manufacturing:

### 🔧 Your Steel Fabrication Operations
- **Structural Steel**: Beams, columns, plates, angles, channels
- **Sheet Metal**: Cutting, bending, welding, painting
- **Custom Fabrication**: Project-based manufacturing
- **Multi-stage Production**: Fabrication → Painting → Dispatch

### 💡 Problems Solved

| Challenge | Our Solution |
|-----------|--------------|
| 📋 **Complex steel quotes** | Detailed BOMs with material dimensions, weight calculations |
| ⏱️ **3-Stage production tracking** | Real-time Fabrication → Painting → Dispatch workflow |
| 📦 **Raw material by dimensions** | Stock by size (2000x1000x6mm), weight tracking |
| ♻️ **Scrap & waste management** | Post-dispatch scrap CSV upload, classify, return to inventory |
| 🔄 **Reusable offcuts** | Track usable pieces, find matches for new orders |
| 📊 **Loss minimization** | Scrap rate analytics, recovery tracking, waste reduction |

## ✨ Steel-Specific Features

### 🏭 Production Module (MES)
- **3-Stage Tracking**: Fabrication completion → Painting → Ready for dispatch
- **Auto-deduction**: Material automatically deducted at fabrication completion
- **Work orders**: Generated from customer orders
- **Quality control**: Inspection at each stage

### 📋 Customer & Project Management
- **Excel upload**: Bulk import customer orders with material specs
- **Project tracking**: Full lifecycle from quote to delivery
- **Material requirements**: Auto-calculate from project specs

### 📦 Inventory Management
- **Dimension-based stock**: Sheet 2000x1000x6mm, Beam 150x75x6m
- **Weight tracking**: Auto-calculate from dimensions
- **Material certificates**: Heat numbers, mill test reports
- **Low stock alerts**: Automatic replenishment notifications

### ♻️ Scrap & Reusable Inventory
- **Post-dispatch scrap upload**: CSV upload after project completion
- **Auto-classification**: Group by size, material, reason
- **Reusable stock**: Track offcuts that can be used again
- **Find-match feature**: Search reusable pieces for new orders
- **Dispose or return**: Mark as waste or return to inventory

### 💰 Loss Analytics Dashboard
- **Scrap Rate %**: Monitor waste percentage
- **Recovery Rate**: Track material recovered
- **Estimated Loss Value**: Financial impact of waste
- **Trend Analysis**: 30-day rolling analytics

## 🚀 Quick Start

### Prerequisites
- PHP 8.2+
- Composer
- MySQL 8.0+ / PostgreSQL
- Node.js 18+
- Redis (optional, for queues)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/kumar-steel-erp.git
cd kumar-steel-erp

# Install PHP dependencies
composer install

# Install Node dependencies
npm install && npm run build

# Environment setup
cp .env.example .env
php artisan key:generate

# Database setup
php artisan migrate
php artisan db:seed

# Start development server
php artisan serve
```

### Docker Installation

```bash
docker-compose up -d
```

Access at: http://localhost:8000

## 📁 Project Structure

```
├── app/
│   ├── Models/          # Eloquent models (Products, Orders, Scrap, etc.)
│   ├── Http/Controllers # Business logic controllers
│   ├── Livewire/        # Real-time components
│   └── Services/        # Business services
├── config/              # Application configuration
├── database/
│   ├── migrations/      # Database schema
│   └── seeders/         # Sample data
├── resources/
│   ├── views/           # Blade templates
│   └── lang/            # Translations
└── routes/              # Web and API routes
```

## 🔐 Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@kumarbrothers.com | admin123 |

**⚠️ Change default credentials immediately after installation!**

## 📊 Key Modules

| Module | Description |
|--------|-------------|
| **Dashboard** | KPIs, charts, alerts, loss analytics |
| **Customers** | CRM with project history |
| **Products** | Material master with dimensions |
| **Inventory** | Stock by location, movements |
| **Orders** | Quote → Order → Delivery workflow |
| **Production** | Work orders, 3-stage tracking |
| **Scrap** | Post-dispatch waste management |
| **Reusable** | Offcut tracking and matching |
| **Quality** | Inspections, non-conformities |
| **Reports** | Analytics and exports |

## 🛠️ Configuration

### Steel-Specific Settings

Edit `config/steel.php` for:
- Default material types
- Dimension formats
- Weight calculation formulas
- Scrap reason codes
- Quality grades

### Environment Variables

```env
APP_NAME="Kumar Brothers Steel ERP"
DB_DATABASE=kumar_steel_erp

# Steel-specific
STEEL_DEFAULT_DENSITY=7850  # kg/m³
SCRAP_AUTO_CLASSIFY=true
REUSABLE_MIN_SIZE=100       # mm
```

## 📄 License

This software is licensed under the MIT License.

Built with ❤️ for Kumar Brothers Steel Fabrication

---

**Kumar Brothers Steel** - Quality Steel, Reliable Delivery
