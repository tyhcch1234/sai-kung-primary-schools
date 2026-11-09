# 西貢區小學公開資料網站

沿用原儲存庫 `tyhcch1234/sai-kung-primary-schools` 和原 GitHub Pages URL：

<https://tyhcch1234.github.io/sai-kung-primary-schools/>

米白／深綠分析版、原 favicon、繁體中文、無網路字型、外部 JavaScript 或 CDN。研究範圍依輸入 `scope_notes`，**西貢行政區不等同 95 校網**。不建立替代 Manus 專案、不改其他儲存庫或全站登入設定。

## 目前工作狀態

研究內容已完成：輸入為39校的真實研究JSON、策略及可讀報告；缺數、未核實、口徑限制與矛盾仍明示保留。`build_site.py`、`styles.css`、`app.js` 及 `manus-routes.json` 為原GitHub Pages專頁的產生器與前端，並非替代Manus專案。2026-11-09已恢復儲存庫擁有人授權；此版本經原儲存庫 `main` 分支根目錄發布，實際上線狀態以GitHub Pages建置及原網址內容為準。合成測試fixture不會写入儲存庫 `data.json`。

產生器不搜尋、不研究、不核實來源内容、不補完事實、不從旧頁讀取任何學校數據。它只從原首頁讀取 favicon。本次只更新原小學專頁，未對任何學校聯絡。

## 易讀版閱讀方式

首頁依序為短結論及六項覆蓋数字、搜尋與學校摘要卡、逐級比較、公開升中去向、社媒、策略及来源。主要入口是「搜尋及查看學校」；總覽的完整統計定義與研究範圍按需展開。覆蓋數字仍為39／15／11／10／20／3，沒有按篩選重算，也不是跨年招生市場總量。

校卡未展開已可看校名、類別、小學段總數／小六及學年、最多三個原資料活動標籤和FB／IG／小紅書身份狀態。主紀錄欠缺可用實數時，摘要只可選最新學年的 `official_exact` 歷史實數，明示「歷史資料」與學年；不使用媒體約數、學額、矛盾總數或包含其他學段／校區數字。非標準小六不以歷史資料冒充本地P6。**篩選及排序仍依主紀錄**，不因摘要帶出歷史數值而改變。

每校詳情分「學生人數」「重點活動」「升中去向與制度」「社交平台」「宣傳切入與聯絡」「來源與資料限制」六節，只有人數節預設開啟。每份歷年人數、每屆去向、長證據、來源及原始附加欄位都在初始HTML獨立折疊；沒有合併學年或刪除原備註。技術狀態以繁體中文短說明呈現，原標記留在證據區以供核對。完整來源集中列一次，校卡保留逐項深連結。

逐級比較表及社媒比較預設收起；比較格只列短數值、必要學年及來源，不重複全校長備註。接收中學篩選會自動展開命中學校及其屆別；清除篩選不會擅自收起使用者已展開的內容。`#roster`／`#classes`／`#social` 深連結可開啟相應比較區，校卡及來源深連結會展開所需的祖先折疊。策略以六類提案卡、步驟及渠道卡呈現；逐校接觸長清單與量度資料仍完整、預設收起。

樣式與互動資產共用 `v=readable20261109` 快取版本；沒有新字型、圖片、外部CDN或研究資料。2026-11-09易讀版屬呈現更新，發布狀態仍需依原GitHub Pages建置確認。

## 重建（Python 3.10+，零額外套件）

```bash
python3 build_site.py \
  --data data.json \
  --strategy strategy.json \
  --report report.md
```

產生器預設寫入 **腳本所在目錄**，無需安裝 Node 套件、Python 套件或網路存取。重複執行相同輸入結果一致。每次會生成／更新：

| 檔案 | 用途 |
|---|---|
| `index.html` | 完整靜態研究內容；無 JavaScript 也可閱讀每校資料、展開詳情和來源 |
| `styles.css` | 手機優先米白／深綠樣式、鍵盤焦點、減少動態與列印適配 |
| `app.js` | 漸進式搜尋、類別／小六已知篩選、排序、接收中學條件與匯出 |
| `data.json` | 輸入學校 JSON **逐位元組複製**，沒有修改事實 |
| `strategy.json` | 輸入策略 JSON **逐位元組複製** |
| `report.md` | 有 `--report` 時逐位元組複製已完成可讀報告，不改寫來源；未指定時才產生結構化文字fallback，排除raw_data／integration影子JSON |
| `manus-routes.json` | 原主页 `/sai-kung-primary-schools/` 的靜態路由宣告；非部署指令 |

讀取、資料最上層驗證、頁面生成與資產讀取成功後才寫出檔案。各檔案以同目錄臨時檔原子替換；整批不是跨檔案交易，因此磁碟／權限故障仍可能產生半套輸出，發布前需檢查全部檔案。輸入檔不存在、JSON損壞、含非有限數字、最上層格式不符、空 `schools` 或原 favicon 缺失會報錯並拒絕舊資料 fallback。**不自動判斷研究是否已完整**，請人工確認來源、範圍、缺口和學年後才在正式目錄重建。

隔離生成、保留原首頁：

```bash
python3 build_site.py --data /path/to/real-schools.json \
  --strategy /path/to/real-strategy.json --output-dir /tmp/sai-kung-preview
```

隔離目錄亦會包含 CSS、JS、JSON、報告與 route manifest。不要把合成 fixture 的產物發布到原站。

## 輸入契約

資料根物件包含 `checked_date`、`scope_notes`、`schools`、`failures`、`summary`。`schools` 必須是非空陣列；每校預期欄位如下：

```text
id, name, english_name, category, website, profile_url, address, school_net,
status, scope_note, checked_date,
enrolment: {academic_year, total, grades: [{grade, students, classes, source_ids, note}],
            p6, source_ids, note},
enrolment_history: [],
activities: [{title, description, tags, year, source_ids}],
destinations: {academic_year, cohort_total, coverage, note,
               schools: [{name, count, percentage, source_ids, note}], source_ids},
destinations_history: [],
preferences: {observed, inference, caveat, source_ids},
school_links: [{school, relationship, note, source_ids}],
social: [{platform, platform_normalized, account, url, status, verification, source_ids}],
contact: {phone, email, source_ids},
marketing: {segment, priority_rationale, entry_offer, contact_role, message, channels, caveats},
sources: [{id, title, url, academic_year, accessed_date}], gaps: []
```

策略根物件包含：

```text
context, main_conclusion,
segments: [{name, rationale, school_ids, offer, message, channels}],
priority: [{school_id, reason, evidence_gap}],
timeline: [{period, action, kpi}],
content_plan: [{channel, audience, content, cta}],
measurement: [], limitations: []
```

其他研究事實在相應靜態附加區保留，完整原始資料則留在下載JSON及內嵌payload。raw_data、integration與內部路徑不在正常HTML重複輸出；每校原始JSON開關首次展開才由JS以安全 `textContent` 填入空pre，無JS仍可下載完整 `data.json`，不另作網路請求。欄位的 null、空陣列、非預期單項／物件／字串會安全、可讀地呈現，不擅自修改輸入。`total`、`p6` 亦支援物件紀錄；核實標記、原報告值、总數範圍、小六適用性、來源及學年均保留。各級／去向單項如有 `academic_year` 優先顯示；只有欄位不存在才沿用集合學年，明示 null 不猜測。班數優先用 `classes_academic_year`，明示未知不繼承全校總數學年。

## 資料紀律

- **沒有班額推算，沒有混年學生人數總計。** 總覽使用研究摘要及其定義：已核實小學總數15校、至少一級實數11校、標準小六在籍實數10校、有校名的已報道升學結果20校、接收中學逐校人數3校。包括定義允許的歷史紀錄，百分比不當人數，政策不當實際結果。只有輸入未提供相應摘要值時，fallback才按主記錄計算並明示「僅主記錄」，不冒充核實統計。
- null 顯示「未公開／未核實」；空字串顯示「未提供」。數字 0 不被替換成缺資料。人數篩選／排序認得非負有限數字及純數值字串；異常值原樣呈現、不當作可排序實數。覆蓋校數不是學年一致或來源已由程式核實的保證。
- 小六使用 `enrolment.p6` 或明示P6／小六年級紀錄；按人數、標準化學年、班數去重，單純note／來源不同不重複，p6物件優先。真正不同數、年或班數全部分開顯示、不相加。多條而無單一排序值時放末，已知小六篩選仍保留有實數學校。
- 國際／特殊學制保留所有原年級及註記。`Grade 6`、`Year 6` 不自動等同P6。`not_a_standard_primary_P6`明示「不適用（非標準小六學制）」，不是缺數。來源平均4班不是本級實際班數，顯示「來源列平均4班，非本級實際班數；班數年份未明」。
- 主及歷年總數核實狀態含未解矛盾時，正常指標明示例如「原表列450（總數有矛盾）」且不作total_sort；原報告值仍保留，不無保留當實數。
- 全部主及歷年接收中學逐屆分表，不截取前幾名；每表保留學年、該屆總人數、覆蓋範圍及備註。搜索納入主及歷年實際結果校名，每校仍僅一個總覽外層article，避免重複計校數。政策另標「非已觀察實際去向」，不納入實際結果篩選。百分比僅按輸入公布值顯示，不自行推算；列項小計非全屆分母。
- 派位／錄取去向不等於第一志願。取向的 `observed`、`inference`、`caveat` 分開。學校關係不等於實際派位紀錄。
- Facebook、Instagram、小紅書每校固定明示狀態與身份證據，其他平台完整顯示。`status` 與 `verification` 按原始研究呈現；程式不由網址或名稱判為官方，校友會／第三方不納入官方帳戶統計。
- 易讀摘要的社媒徽章使用 `verification_status_normalized` 及 `account_scope` 精確分類，不用「官方」「校友」等模糊關鍵字猜測身份；缺少標準化值時保守標為未標準化，原始狀態與證據仍可展開。
- 數字／字串來源 ID 可互相對應。無來源ID會明示；ID不存在顯示「未能對應」，在頁面與報告附提醒而不崩潰。來源存在只表示資料聯結有效，不證明內容正確。
- 策略以 **中學面向P5/P6家庭／小學** 為暫定情境：分群、切入、接觸考量、內容、渠道、時間線、量度與限制。不是學校排名，必須由委託方確認情境與接洽授權。

## 功能、可及性與安全

所有學校內容在初始 HTML；JavaScript 只增強，不負責取資料或建立研究內容。無 JavaScript 可讀名冊、活動、全部去向、社媒、聯絡、策略、缺口與來源，亦可下載完整檔案。

搜尋校名／英文名／活動／接收中學、類別、已知小六與排序一起控制名冊、校卡、社媒及來源，顯示数量以 `aria-live` 回饋。升中總覽額外有接收中學搜尋與選單；它不改校卡內原始完整去向表。清除條件、展開／收起、班數小字切換均為鍵盤可用原生控制項。

深連結格式 `#school-<id>`；不適合作HTML ID的字串用穩定雜湊，缺失ID使用原紀錄位置，重複ID保留独立紀錄。有效深連結會展開、定位及聚焦，即使該校被篩選隱藏也會清除條件後顯示。沿用旧 `#overview`、`#classes`、`#roster`、`#profiles`、`#social`、`#promo`、`#method` 錨點；沒有創造舊校卡從未提供的ID。

提供當前學校篩選JSON與人數CSV匯出；JSON保留完整學校字段及原研究背景，`summary`/`failures`/`scope_notes` **仍是全資料背景，並未按篩選重算**。CSV包含主＋enrolment_history，各全校、原年級及獨立小六行明示不跨年／不與年級行重複相加；並列核實狀態、原報告值、總數範圍、小六適用性、班數口徑、班數來源學年／ID、原報告班數、來源備註及0。矛盾數字只留原報告值，實數列為未知。完整活動／去向／策略請下載JSON。CSV雙引號、內引號加倍、UTF-8 BOM及既有防公式注入保護不變。

動態文字／屬性與內嵌JSON已轉義。外部可點連結僅接受合法HTTP／HTTPS網址，不接受帳密、控制字元、反斜線、JavaScript或data來源連結。原頁受信任 favicon 的 SVG data URL單獨保留，並非研究資料輸入。沒有 `eval`、外部JS／CDN、登入或追蹤碼。電話、電郵保留為文字，不設自動寄信／拨號。

有 skip link、清晰焦點、原生 `details`、區域式橫向捲動、表格標頭與標題、減少動態和列印樣式。啟用JS列印時會暫時展開所有詳情及來源；列印樣式取消篩選隱藏，輸出所有學校。無JS由CSS協助显示內容，但不同瀏覽器對關閉 `details` 的列印處理可能有差異；可先逐校展開或閱讀／下載報告。没有瀏覽器截图或跨裝置視覺實測。

Title、description、canonical 與文字 Open Graph metadata 已在初始HTML使用原絕對網址；沒有裝飾分享圖片。`manus-routes.json` 只是來源的路由清單，不代表任何Managed專案或部署狀態。

## 本地檢查

```bash
python3 -m py_compile build_site.py test_build_site.py
node --check app.js
python3 test_build_site.py
```

`test_build_site.py` 是標準函式庫契約測試：只在自動清理的 `/tmp` 臨時目錄建立**合成、非學校研究**fixture，保留原十一項靜態完整性、逐項學年、0／null、不規則資料、來源聯結、HTML/URL安全、重複build、原首頁不變及Node篩選／排序與CSV防注入契約，另加四項閱讀順序、預設折疊、歷史官方實數與P6不適用、社媒精確分類及命中去向祖先展開檢查。不使用瀏覽器、搜尋或網路。真實資料須另外檢查母名單完整、來源可信度、學年與去向覆蓋；程式測試不能代替研究審核。

## 發布邊界

本次獲授權只更新 `tyhcch1234/sai-kung-primary-schools`。原GitHub Pages設定為 `main` 分支、根目錄；不改全站首頁保護、其他頁面或其他儲存庫，不建立替代網站，不強制推送或重寫歷史。發布成功須同時核對GitHub Pages建置結果及原網址內容。
