# Contributing to Kumar Brothers Steel ERP

We welcome contributions to improve the steel fabrication ERP system!

## How to Contribute

### Reporting Issues
- Use the internal issue tracker
- Include steps to reproduce
- Attach screenshots if applicable

### Code Contributions
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Follow PSR-12 coding standards
4. Write tests for new functionality
5. Submit a pull request

### Coding Standards
- PHP: PSR-12
- JavaScript: ESLint with Airbnb config
- Blade templates: 4-space indentation
- Database: Snake_case for columns

### Commit Messages
```
type(scope): description

[optional body]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example: `feat(scrap): add CSV bulk upload for post-dispatch scrap`

## Development Setup

```bash
# Clone and install
git clone [repo-url]
composer install
npm install

# Run tests
php artisan test

# Code style check
./vendor/bin/pint
```

---

**Kumar Brothers Steel** - Building Together
