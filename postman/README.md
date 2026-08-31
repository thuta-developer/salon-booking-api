# Salon Booking API — Postman စမ်းသပ်မှု လမ်းညွှန်

## 1. Import လုပ်ပုံ
1. Postman ကို ဖွင့်ပါ → **Import** နှိပ်ပါ
2. `Salon-Booking-API.postman_collection.json` ကို drag/drop (သို့) file select လုပ်ပါ
3. `Local.postman_environment.json` ကိုပါ import လုပ်ပါ
4. ညာအခြေမှာ environment dropdown မှ **Salon Booking — Local** ကို ရွေးပါ

## 2. Server စတင်ရန်
```bash
docker compose up -d        # db + redis + api
curl http://localhost:8000/health   # {"status": "ok"} ရရင် အဆင်သင့်
```

## 3. စမ်းသပ်အစဉ် (Run Order)
| အဆင့် | Request | မျှော်မှန်း Result |
|---|---|---|
| 1 | Auth → **Login — Super Admin** | 200 — token ၂ ခု auto-save ဖြစ်သည် |
| 2 | Auth → Me | 200 — admin အကောင့် အချက်အလက်များ |
| 3 | Users → List Users | 200 — ပထမ user id ကို `{{user_id}}` သိမ်းသည် |
| 4 | Users → Get/Update/Delete | 200 |
| 5 | Permissions → Create Permission | 201 — `{{perm_id}}` auto-save |
| 6 | Roles → Create Role | 201 — `{{role_id}}` auto-save |
| 7 | Roles → Assign Permissions To Role | 200 |
| 8 | Roles → Assign Roles To User | 200 |
| 9 | Auth → Refresh Token | 200 — token အသစ်များ rotate ဖြစ်သည် |
| 10 | Auth → Logout | 200 — ပြီးရင် Me ပြန်ခေါ်ကြည့်ပါ → **401** |

## 4. Test Accounts
| Role | Email | Password |
|---|---|---|
| Super Admin | `admin@gmail.com` | `Admin@12345` |
| Customer | `postman@test.com` | `PostmanTest123` |

> Password reset လုပ်ချင်ရင်: `python3 -m app.db.seed` (သို့) DB ထဲ တိုက်ရိုက် update လုပ်ပါ။

## 5. Security Fixes များကို စမ်းကြည့်ရန် (Negative Tests folder)
- **Wrong password** → 401 (timing-attack ကာကွယ်ထားသဖြင့် user မရှိသလောက် တုန့်ပြန်မှု အချိန် တူညီမှုရှိသည်)
- **No token** → 401
- **Customer က user list ခေါ်** → 403 (RBAC)
- **Password mismatch** → 400
- **Duplicate email** → 400 (email case ကွာကွာဖြစ်ဖြစ် ထပ်နေရင် ပယ်ချသည်)
- **Brute-force** → bad password ၅ ခါ ဆက်တိုက် run ပါ → 5 ခါမြောက်မှာ **429 + Retry-After** (15 မိနစ် lock)

Lock ဖြေရန်:
```bash
docker exec salon_redis redis-cli FLUSHDB
```

## 6. Token ပြန်ရနိုးရိုး (Token ပြဿနာရှိရင်)
`access_token` သက်တမ်းကုန်ရင် (expired) နောက်ထပ် 401 တွေ များလာရင် — Auth → **Login — Super Admin** ကို ပြန် run ပါ။ Collection variable တွေ အလိုအလျောက် အသစ်ဖြစ်သွားပါမယ်။

## 7. Collection ပြန်ဆောက်ချင်ရင်
```bash
python3 postman/build_collection.py
```
