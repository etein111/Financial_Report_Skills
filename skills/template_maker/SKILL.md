---
name: template_maker
description: Î¬Ê¦Ä£å¡£Ã»ÒªÄ£å¡¢ Word Äµá¹¹ schemaÎ¬Ä£Ö¶Î»Ö¤Ä£Ê±Ê¹Ã´ skillÖ§Ö½Ê½Õ¼Ô¶Ä£Ê½invoke.py Å±
---

# template_maker

Î¬Ê¦Ä£å¡£

## 

ÏµÍ³Ö§ÖµÄ³Í£

|  | Ëµ |
|---------|------|
| `company` | Ë¾Ç±æ£¨×´Î¸Ç¡È·È£ |
| `sector` | ÒµÐ¾ |
| `company_flash` | Ë¾Ñ¶ |
| `sector_flash` | ÒµÑ¶ |
| `macro` | Û±æ£¨Í¨ common Ä£å£© |
| `strategy` | Ô±æ£¨Í¨ common Ä£å£© |
| `quantitative` | æ£¨Í¨ common Ä£å£© |
| `bond` | Õ®È¯æ£¨Í¨ common Ä£å£© |

**×¢**
-  `router.yaml` Ã£Ê¹Ð¡Ð´
- ö±¨¸Í¿Ó³äµ½Í¬Ò»Ä£
- ç£º`macro``strategy``quantitative``bond` Ó³äµ½ `common` Ä£
- Í²Ð±É¸ÒµÒªÕ¹

## 

Ã»ó´´½Î¬Ä£Ê±Ê¹**Ê½**

### Ô­

- **Ò»Ö»Ò»**
- **á¹©Æ¼ÖµÄ¬Öµ**
- **Ö¶Ô»Õ¼Ï¢**

### 

1. **È·Ä£ÆºÍ±**
   - Ê¾Ø¸"ÃµÄ£ `common` Ä£å£¬ macrostrategy È±Í¡á¹© Word Ä¼Â·"

2. **È¡ Word Ä¼Â·**
   - Ö¤Ä¼
   - Ô¶ elements.yaml
   - âµ½Ñ¡Ä¼Ã»Ñ¡

3. **Ñ¯ÕªÒª**
   - ÕªÒªÎ»Ñ¯Ê£ë£©
   - Î»Ñ¯Ê£Ñ¡flash Ã»Ä£
   - ÖªÃ»Ø¼á¹¹
     - **ÕªÒªÒ»Ð»Ò³** Word ÎªÖ½Ú£
     - **Ä£Ò»Ò³Ä½Ò²Ð»Ò³**
     - **Â¼Ï¢Â¶Ò»ÂµÒ»Ò³Ê¼**

4. **È·Ï²Ö´**
   - Õ¹Ê¾Ï¢
   - Ñ¯Ê£"È·Ï´"

### Ö´

È·Ïºó£¬°Â²è´´Ä£å£º

1.  Word Äµ elements.yaml
2. É±Æ½ schema.yaml
3. æ»»Ä£ÐµÖ¶ÖµÎªÕ¼Î»
4. æ»»ÕªÒª
5.  router.yaml Â·
6. Ä£Ä¼

É¹ó´´½Ä¼á¹¹

```
templates/
 router.yaml           # Ô¶Â·
 <Ä£>/
     meta.yaml         # Ä£Ôª
     schema.yaml       # Ö¶ schemaÆ½á¹¹
     template.docx     # Word Ä£Ä¼
```

## schema.yaml á¹¹

Éµ schema.yaml **Æ½á¹¹**

```yaml
# === Í¨Ö¶Î£ÄµÈ¡Ä£å£©===
company:
  description: Ë¾
  format: É»

ticker:
  description: Æ±
  format: 2507.HK

rating:
  description: 
  format: Ú´

# === Word Æ¬Î£Ô­Ê¼ÄµÕªÈ¡Îª Word Ä¼===
abstract:
  type: fragment
  description: ÕªÒª
  scope: Ò³Ò²à£¨Ä»ÜµÚ¶Ò³
  hints:
    - Í¨Í¶ã¡¢Ä¹Ûµ
    - Ô¼ 200-500 
    - Î»Ò³Ò²

body:
  type: fragment
  description: Ä²
  scope: Ò³Ö®óµ½±Î²
  hints:
    - Â½Ï¸
    - Ü°Í¼
    - Ô­Ä½á¹¹Í±ã¼¶
```

**Ö¶Ëµ**
- **Í¨Ö¶** `type`ÄµÈ¡Ö¶ÖµÉ±Ê±äµ½Ä£
- **Word Æ¬**`type: fragment`Ô­Ê¼ÄµÕªÈ¡ Word Æ¬Ä¼ document_maker Ê¹

**ÒªËµ**
- `abstract`ÕªÒªÇ±Ä£Ð±Í¶
- `body`Ä£Ç¿Ñ¡Ä£ flash Í¨Ã»

## Ô¶Ä£Ê½

Ô¶Ö±Ê¹ `scripts/invoke.py` Å±

```bash
# Ê½È·Ï£
python skills/template_maker/scripts/invoke.py \
  --name common \
  --word fixtures/macro_sample.docx \
  --elements "fixtures/macro_sample elements.yaml"

# Ô¶Ä£Ê½È·Ï£
python skills/template_maker/scripts/invoke.py \
  --name company \
  --word fixtures/company_sample.docx \
  --elements "fixtures/company_sample elements.yaml" \
  --auto-confirm

# Ñ¶æ£¨Ä£
python skills/template_maker/scripts/invoke.py \
  --name company_flash \
  --word fixtures/flash_sample.docx \
  --elements "fixtures/flash_sample elements.yaml" \
  --no-body \
  --auto-confirm

# Ô¶ÕªÒª/Î»
python skills/template_maker/scripts/invoke.py \
  --name custom \
  --word fixtures/custom.docx \
  --elements fixtures/custom_elements.yaml \
  --abstract-scope "Ò³Ú¶" \
  --body-scope "ÓµÂ¿Ê¼" \
  --auto-confirm
```

**Ëµ**
- `--name`: Ä£Æ£è£©
- `--word`: Word Ä¼Â·è£©
- `--elements`: elements.yaml Ä¼Â·è£©
- `--abstract-scope`: ÕªÒªÎ»Ä¬: "Ò³Ò²"
- `--body-scope`: Î»Ä¬: "Ò³Ö®óµ½±Î²"
- `--no-body`: Ñ¶æ£¬Ã»Ä²
- `--output-dir`: Ä¿Â¼Ä¬: templates
- `--auto-confirm, -y`: È·Ï£Ö±Ó´

## elements.yaml Ô¶

ÏµÍ³Ë³ `elements.yaml`

1. `<word_name> elements.yaml`
2. `<word_name>_elements.yaml`
3. `elements.yaml`Í¬Ä¿Â¼

## Ä£

Ê½Æ£Ö°Îª 6 Ä£é£º

| Ä£ |  | Ö° |
|------|--------|------|
| `router.py` | 6 | Â·Ã¹Ð´ë£©|
| `schema.py` | 6 | Schema ÉºÍ¸Â£Ð´ë£©|
| `validate.py` | 1 | Ä£Ö¤ |
| `document.py` | 9 | Äµá¹¹ |
| `template.py` | 10 | Ä£Ý² |

**Ø¼Ô£**
- Æ£ß¼ I/O ë£©
- Ö§÷£¨¼Ä¼ I/O
- Document ó´«µÝ£Ø¸ Word Äµ

## Ä£Ä¿Â¼á¹¹

```
templates/
 router.yaml           # Â·
 <Ä£>/
     meta.yaml         # Ä£Ôª
     schema.yaml       # Ö¶ schemaÆ½
     template.docx     # Word Ä£Ä¼
```

## elements.yaml 格式

elements.yaml 采用**扁平化结构**，所有字段都是简单的键值对。

### 基础字段

```yaml
company: 西锐飞机
ticker: 2507.HK
target_price: 15.0
rating: 买入
```

### 分析师字段（支持多个分析师）

分析师字段采用扁平化命名：`a{序号}_{属性}`，支持 `a1_*` 到 `a8_*`。

```yaml
# 第一个分析师
a1_cn: 杨斌
a1_en: Bin Yang
a1_sfc: BSQ313
a1_email: harryyang@hfisec.com.hk

# 第二个分析师（可选）
a2_cn: 张三
a2_en: Zhang San
a2_sfc: XXX123
a2_email: zhangsan@hfisec.com.hk

# ... 支持 a3_* 到 a8_*
```

**设计说明：**
- 扁平化结构避免模板中的循环处理
- 所有分析师字段都预定义在模板中（固定布局）
- 字段命名规则：`a{序号}_{属性}`，属性包括 `cn`, `en`, `sfc`, `email`


## Ê¹Ê¾

### Ê¾ 1: Í¨Ä£

**Ã»**`Ò»Í¨Ä£`

**AI**ë´´Ê²Ã´ÍµÄ£å£¿ç£ºcommon Í¨Ä£å¡¢company Ë¾æ£©

**Ã»**`common`

**AI**ÃµÄ£ `common` Ä£å£¬ macrostrategy È±Í¡á¹© Word Ä¼Â·
ç£ºfixtures/macro_sample.docx

**Ã»**`fixtures/macro_sample.docx`

**AI**âµ½ `fixtures/macro_sample elements.yaml`Ê¹Ã¸Ä¼

ÒªÕªÒªÄµÄ³È¡

**ÕªÒªÃ£**
- ÕªÒªÒ»Ð»Ò³
- Í¨Ò³Ä±Ð£Ò²

ÕªÒªÄµÄ¸Î»Ã£

**Ã»**`Ò³Ò²`

**AI**ÃµÄ¡Ä²Ö¡

**Ä½á¹¹**
- Ä£Ò»Ò³Ä½Ò²Ð»Ò³
- Â¼Ï¢Â¶Ò»ÂµÒ»Ò³Ê¼

Ý±Ç·Ä²Ö£Ð£ï¿ªÊ¼

**Ã»**`Ò³Ö®'Â¼APPENDIX'Ö®Ç°`

**AI**Ë¡

****
- Ä£Æ£common
- Word Ä¼fixtures/macro_sample.docx
- elements.yamlfixtures/macro_sample elements.yaml
- ÕªÒªÎ»Ã£Ò³Ò²à£¨Ä»ÜµÚ¶Ò³
- Î»Ã£Ò³Ö®Ê¼

È·Ï´

### Ê¾ 2: Flash æ£¨Ä£

**Ã»**`Ò» flash Ä£`

**AI**ë´´Ê²Ã´ÍµÄ£å£¿

**Ã»**`company_flash`

**AI**ÃµÄ£ `company_flash` Ä£å¡£á¹© Word Ä¼Â·

**Ã»**`fixtures/company_flash_sample.docx`

**AI**âµ½ `fixtures/company_flash_sample elements.yaml`Ê¹Ã¸Ä¼

ÕªÒªÄµÄ¸Î»Ã£

**Ã»**`Ò³Ò²`

**AI**ÃµÄ¡Ý±Ç·Ä²Ö£

**Ã»**`Ã»Ä£ flash `

**AI**Ë¡

****
- Ä£Æ£company_flash
- Word Ä¼fixtures/company_flash_sample.docx
- elements.yamlfixtures/company_flash_sample elements.yaml
- ÕªÒªÎ»Ã£Ò³Ò²
- Ä£

È·Ï´

