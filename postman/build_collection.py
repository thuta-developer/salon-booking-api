#!/usr/bin/env python3
"""Postman collection/environment generator for Salon Booking API.

Run:
    python3 postman/build_collection.py

Creates:
    - postman/Salon-Booking-API.postman_collection.json
    - postman/Local.postman_environment.json

Login request များသည် token များကို collection variables
({{access_token}}, {{refresh_token}}) ထဲ အလိုအလျောက် သိမ်းပေးသည်။
"""
import json
import pathlib
import uuid

HERE = pathlib.Path(__file__).parent
API = "{{base_url}}/api/v1"


def _url(path: str, query=None) -> dict:
    """Build a Postman URL object. `path` is relative to /api/v1."""
    clean = path.strip("/")
    parts = ["{{base_url}}", "api", "v1"] + clean.split("/")
    if path.endswith("/"):
        parts.append("")
    url = {"raw": f"{API}/{path}", "host": ["{{base_url}}"], "path": parts}
    if query:
        url["query"] = [{"key": k, "value": v} for k, v in query]
    return url


def req(name, method, path, body=None, query=None, tests=None,
        noauth=False, description=None) -> dict:
    item = {"name": name}
    r = {"method": method, "url": _url(path, query)}
    if noauth:
        r["auth"] = {"type": "noauth"}
    if body is not None:
        r["header"] = [{"key": "Content-Type", "value": "application/json"}]
        r["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2),
                     "options": {"raw": {"language": "json"}}}
    item["request"] = r
    if description:
        item["description"] = description
    if tests:
        item["event"] = [{"listen": "test",
                          "script": {"type": "text/javascript", "exec": tests}}]
    return item


def folder(name, items, description=None) -> dict:
    f = {"name": name, "item": items}
    if description:
        f["description"] = description
    return f


def status(code: int) -> list:
    return [f"pm.test('Status is {code}', "
            f"() => pm.response.to.have.status({code}));"]


SAVE_TOKENS = status(200) + [
    "const json = pm.response.json();",
    "if (json.access_token) {",
    "    pm.collectionVariables.set('access_token', json.access_token);",
    "}",
    "if (json.refresh_token) {",
    "    pm.collectionVariables.set('refresh_token', json.refresh_token);",
    "}",
]

REGISTER_BODY = {
    "email": "newuser@test.com",
    "password": "Password123",
    "confirm_password": "Password123",
    "full_name": "New User",
    "phone_number": "09999999999",
}

# --------------------------------------
# 1. Auth folder
# --------------------------------------

auth_folder = folder("Auth", [
    req("Register", "POST", "auth/register", body=REGISTER_BODY,
        noauth=True, tests=status(201) + [
            "const json = pm.response.json();",
            "pm.test('Returns created user email', "
            "() => pm.expect(json.email).to.eql('newuser@test.com'));",
        ],
        description="Public registration. Duplicate email → 400, "
                    "password mismatch → 400, weak password → 422."),
    req("Login — Super Admin", "POST", "auth/login",
        body={"email": "admin@gmail.com", "password": "Admin@12345"},
        noauth=True, tests=SAVE_TOKENS,
        description="⭐ ဒီ request ကို အရင် run ပါ — access/refresh tokens "
                    "ကို collection variables ထဲ အလိုအလျောက် သိမ်းပေးသည်။"),
    req("Refresh Token", "POST", "auth/refresh",
        body={"refresh_token": "{{refresh_token}}"}, noauth=True,
        tests=SAVE_TOKENS,
        description="Old refresh token ကို revoke ပြီး rotation လုပ်သည် "
                    "(new tokens auto-saved)."),
    req("Me", "GET", "auth/me", tests=status(200)),
    req("Logout", "POST", "auth/logout", tests=status(200),
        description="Current access token ကို Redis blacklist ထဲ revoke "
                    "လုပ်သည်။ Logout ပြီးရင် Me ကို ပြန်ခေါ်ကြည့်ပါ → 401."),
], description="Run order: Login → Me → Refresh → Logout. "
               "Login တိုင်း token အသစ်များ auto-save ဖြစ်သည်။")

# --------------------------------------
# 2. Users folder
# --------------------------------------

users_folder = folder("Users", [
    req("List Users (search / filter / paginate)", "GET", "users/",
        query=[("page", "1"), ("size", "20"), ("search", ""),
               ("account_type", ""), ("is_active", "")],
        tests=status(200) + [
            "const json = pm.response.json();",
            "pm.test('Paginated shape', () => {",
            "    pm.expect(json).to.have.property('items');",
            "    pm.expect(json).to.have.property('total');",
            "    pm.expect(json).to.have.property('total_pages');",
            "});",
            "if (json.items && json.items.length > 0) {",
            "    pm.collectionVariables.set('user_id', json.items[0].id);",
            "}",
        ],
        description="user:read permission လိုသည်။ ပထမ user ရဲ့ id ကို "
                    "{{user_id}} အဖြစ် auto-save လုပ်သည်။"),
    req("Get User Detail (with roles)", "GET", "users/{{user_id}}",
        tests=status(200)),
    req("Update User", "PUT", "users/{{user_id}}",
        body={"full_name": "Updated Name", "phone_number": "09123456789"},
        tests=status(200),
        description="Non-superuser က is_verified / account_type ပြောင်းပါက "
                    "403. ကိုယ့်ကိုယ်ကို deactivate လုပ်ပါက 400."),
    req("Soft Delete User", "DELETE", "users/{{user_id}}",
        query=[("hard_delete", "false")], tests=status(200),
        description="Default = soft delete (reversible)."),
    req("Hard Delete User (superuser only)", "DELETE", "users/{{user_id}}",
        query=[("hard_delete", "true")], tests=status(200),
        description="Non-superuser ဆိုလျှင် 403 Forbidden ရမည်။"),
], description="user:read / user:update / user:delete permissions လိုသည်။ "
               "Super Admin (is_superuser) ကပဲ အားလုံး ခေါ်နိုင်သည်။")

# --------------------------------------
# 3. Roles folder
# --------------------------------------

roles_folder = folder("Roles", [
    req("Create Role", "POST", "roles/",
        body={"name": "Receptionist", "description": "Front desk staff",
              "permission_ids": []},
        tests=status(201) + [
            "const json = pm.response.json();",
            "if (json.id) { pm.collectionVariables.set('role_id', json.id); }",
        ],
        description="role:create permission လိုသည်။ အသစ်ဆောက်တဲ့ role id ကို "
                    "{{role_id}} အဖြစ် auto-save လုပ်သည်။ "
                    "permission တွေ ချိတ်ချင်ရင် အောက်မှ Assign Permissions "
                    "request ကို သုံးပါ (အရင် Create Permission run ရန်)。"),
    req("List Roles (search / paginate)", "GET", "roles/",
        query=[("search", ""), ("page", "1"), ("size", "20")],
        tests=status(200)),
    req("Get Role By ID", "GET", "roles/{{role_id}}", tests=status(200)),
    req("Assign Permissions To Role", "POST", "roles/{{role_id}}/permissions",
        body={"permission_ids": ["{{perm_id}}"]},
        tests=status(200),
        description="⚠️ အရင်ဆုံး Permissions → Create Permission ကို run ပြီး "
                    "မှ ခေါ်ပါ ({{perm_id}} လိုသည်)။"),
    req("Assign Roles To User", "POST", "roles/users/{{user_id}}/assign-roles",
        body={"role_ids": ["{{role_id}}"]}, tests=status(200),
        description="user:update permission လိုသည်။ Non-superuser က "
                    "'Super Admin' role grant လုပ်ပါက 403. "
                    "Superuser ရဲ့ roles ကို ပြင်ပါက 403."),
    req("Delete Role", "DELETE", "roles/{{role_id}}", tests=status(200),
        description="System roles (Super Admin / Customer) ကို delete "
                    "လုပ်ပါက 400/403 ရမည်။"),
], description="Run order: Create Role → Assign Permissions → "
               "Assign Roles To User → Delete Role.")

# --------------------------------------
# 4. Permissions folder
# --------------------------------------

permissions_folder = folder("Permissions", [
    req("Create Permission", "POST", "permissions/",
        body={"name": "booking:create", "description": "Can create bookings",
              "module": "Booking"},
        tests=status(201) + [
            "const json = pm.response.json();",
            "if (json.id) { pm.collectionVariables.set('perm_id', json.id); }",
        ],
        description="permission:create လိုသည်။ id ကို {{perm_id}} အဖြစ် "
                    "auto-save လုပ်သည်။"),
    req("List Permissions (search / module / paginate)", "GET", "permissions/",
        query=[("search", ""), ("module", ""), ("page", "1"), ("size", "20")],
        tests=status(200)),
    req("Update Permission", "PUT", "permissions/{{perm_id}}",
        body={"description": "Updated description"}, tests=status(200)),
    req("Delete Permission", "DELETE", "permissions/{{perm_id}}",
        tests=status(200)),
])

# --------------------------------------
# 5. Negative Tests (security fixes စမ်းရန်)
# --------------------------------------

negative_folder = folder("Negative Tests (Security)", [
    req("Login — wrong password (expect 401)", "POST", "auth/login",
        body={"email": "admin@gmail.com", "password": "WrongPassword!"},
        noauth=True, tests=status(401)),
    req("Access protected endpoint without token (expect 401)",
        "GET", "users/", noauth=True, tests=status(401)),
    req("Login as Customer", "POST", "auth/login",
        body={"email": "postman@test.com", "password": "PostmanTest123"},
        noauth=True, tests=SAVE_TOKENS,
        description="Customer token ကို save လုပ်သည် — အောက်ပါ 403 test အတွက်။ "
                    "ပြီးရင် Super Admin Login ကို ပြန် run ပါ။"),
    req("Customer hits user list (expect 403)", "GET", "users/",
        tests=status(403),
        description="user:read permission မရှိသော customer ဖြစ်လို့ 403 "
                    "ရရမည် (RBAC working)။"),
    req("Register — password mismatch (expect 400)", "POST", "auth/register",
        body={"email": "mismatch@test.com", "password": "Password123",
              "confirm_password": "Different123", "full_name": "Mismatch",
              "phone_number": "09777777777"},
        noauth=True, tests=status(400)),
    req("Register — duplicate email (expect 400)", "POST", "auth/register",
        body=REGISTER_BODY, noauth=True, tests=status(400),
        description="Register နှစ်ခါ run ပြီးရင် duplicate → 400."),
    req("Lockout test — bad password x5 (expect 429 finally)",
        "POST", "auth/login",
        body={"email": "postman@test.com", "password": "BadPass999"},
        noauth=True,
        description="ဒီ request ကို 5 ခါ ဆက်တိုက် run ပါ — 5 ခါမြောက်မှာ "
                    "429 Too Many Requests + Retry-After header ရမည် "
                    "(15 မိနစ် lock)။ Lock ဖြေရန်: "
                    "docker exec salon_redis redis-cli FLUSHDB"),
])

# --------------------------------------
# Assemble + write files
# --------------------------------------

collection = {
    "info": {
        "_postman_id": str(uuid.uuid4()),
        "name": "Salon Booking API",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/"
                  "collection.json",
        "description": (
            "Salon Booking API (FastAPI) — user / auth / role / permission.\n\n"
            "🚀 **စတင်စမ်းပုံ**\n"
            "1. Local environment ကို select လုပ်ပါ (base_url = http://localhost:8000)\n"
            "2. Auth → **Login — Super Admin** ကို run ပါ (token auto-save)\n"
            "3. ကျန် request များ အစဉ်လိုက် run ပါ — id များ auto-save ဖြစ်သည်\n\n"
            "👤 Super Admin: admin@gmail.com / Admin@12345\n"
            "👤 Customer: postman@test.com / PostmanTest123"
        ),
    },
    "auth": {"type": "bearer",
             "bearer": [{"key": "token", "value": "{{access_token}}",
                         "type": "string"}]},
    "variable": [
        {"key": "base_url", "value": "http://localhost:8000"},
        {"key": "access_token", "value": ""},
        {"key": "refresh_token", "value": ""},
        {"key": "user_id", "value": ""},
        {"key": "role_id", "value": ""},
        {"key": "perm_id", "value": ""},
    ],
    "item": [auth_folder, users_folder, roles_folder, permissions_folder,
             negative_folder],
}

environment = {
    "name": "Salon Booking — Local",
    "values": [
        {"key": "base_url", "value": "http://localhost:8000", "enabled": True},
    ],
}

coll_path = HERE / "Salon-Booking-API.postman_collection.json"
env_path = HERE / "Local.postman_environment.json"
coll_path.write_text(json.dumps(collection, indent=2, ensure_ascii=False),
                     encoding="utf-8")
env_path.write_text(json.dumps(environment, indent=2, ensure_ascii=False),
                    encoding="utf-8")
print(f"Created {coll_path}")
print(f"Created {env_path}")