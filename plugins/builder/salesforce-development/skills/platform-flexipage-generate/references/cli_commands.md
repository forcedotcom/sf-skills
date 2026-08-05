# CLI Command Reference

## RecordPage with fields

```bash
sf template generate flexipage \
  --name Account_Custom_Page \
  --template RecordPage \
  --sobject Account \
  --primary-field Name \
  --secondary-fields Phone,Industry,AnnualRevenue \
  --detail-fields Street,City,State,Name,Phone,Email
```

## AppPage

```bash
sf template generate flexipage \
  --name Sales_Dashboard \
  --template AppPage \
  --label "Sales Dashboard"
```

## HomePage

```bash
sf template generate flexipage \
  --name Custom_Home \
  --template HomePage \
  --description "Custom home for sales team"
```

## Common Options

All templates support:
- `--output-dir` (default: current directory)
- `--api-version` (default: latest)
- `--label` (default: page name)
- `--description`
