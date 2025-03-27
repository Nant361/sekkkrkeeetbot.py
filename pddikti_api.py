import aiohttp
import json
import asyncio
from datetime import datetime

async def login_pddikti(session):
    """Login ke PDDikti dan dapatkan token"""
    try:
        # STEP 1: GET /signin
        await session.get(
            "https://pddikti-admin.kemdikbud.go.id/signin",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        
        # STEP 2: POST /login/login
        login_data = {
            'data[username]': 'MDQzMTc2',
            'data[password]': 'QEA8PkxrajEyMg==',
            'data[issso]': 'false'
        }
        login_response = await session.post(
            "https://api-pddikti-admin.kemdikbud.go.id/login/login",
            data=login_data,
            headers={
                "Origin": "https://pddikti-admin.kemdikbud.go.id",
                "Referer": "https://pddikti-admin.kemdikbud.go.id/",
                "User-Agent": "Mozilla/5.0"
            }
        )
        
        if login_response.status == 200:
            data = await login_response.json()
            i_iduser = data["result"]["session_data"]["i_iduser"]
            id_organisasi = data["result"]["session_data"]["i_idunit"]
            
            # STEP 3: GET /isverified
            await session.get(
                f"https://api-pddikti-admin.kemdikbud.go.id/isverified/{i_iduser}",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            
            # STEP 4: POST /login/roles/1?login=adm
            await session.post(
                "https://api-pddikti-admin.kemdikbud.go.id/login/roles/1?login=adm",
                data={'data[i_iduser]': i_iduser},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            
            # STEP 5: POST /login/setlogin/3/{id_organisasi}
            setlogin_data = {
                'data[i_username]': '043176',
                'data[i_iduser]': i_iduser,
                'data[password]': '@@<>Lkj122',
                'data[is_manual]': 'true'
            }
            setlogin_response = await session.post(
                f"https://api-pddikti-admin.kemdikbud.go.id/login/setlogin/3/{id_organisasi}?id_pengguna={i_iduser}&id_unit={id_organisasi}&id_role=3",
                data=setlogin_data,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            
            if setlogin_response.status == 200:
                setlogin_result = await setlogin_response.json()
                pm_token = setlogin_result["result"]["session_data"]["pm"]
                return i_iduser, id_organisasi, pm_token
        
        print("Login failed")
        return None, None, None
                
    except Exception as e:
        print(f"Error during login: {str(e)}")
        return None, None, None

async def search_student(keyword, i_iduser, pm_token, session):
    """Cari data mahasiswa"""
    try:
        # Cari mahasiswa
        search_data = {
            'data[keyword]': keyword,
            'data[id_sp]': '',
            'data[id_sms]': '',
            'data[vld]': '0'
        }
        
        search_url = f"https://api-pddikti-admin.kemdikbud.go.id/mahasiswa/result?limit=20&page=0&id_pengguna={i_iduser}&id_role=3&pm={pm_token}"
        
        async with session.post(search_url, data=search_data, headers={"User-Agent": "Mozilla/5.0"}) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("result", {}).get("data", [])
            else:
                print(f"Search failed with status {response.status}")
                return []
                
    except Exception as e:
        print(f"Error during search: {str(e)}")
        return []

async def get_student_detail(id_reg_pd, i_iduser, id_organisasi, pm_token, session):
    """Dapatkan detail mahasiswa"""
    try:
        # Dapatkan detail mahasiswa
        detail_url = f"https://api-pddikti-admin.kemdikbud.go.id/mahasiswa/detail/{id_reg_pd}?id_pengguna={i_iduser}&id_unit={id_organisasi}&id_role=3&pm={pm_token}"
        
        async with session.get(detail_url, headers={
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://pddikti-admin.kemdikbud.go.id",
            "Referer": "https://pddikti-admin.kemdikbud.go.id/",
            "Content-Type": "application/json"
        }) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("result", {})
            else:
                print(f"Get detail failed with status {response.status}")
                return {}
                
    except Exception as e:
        print(f"Error getting student detail: {str(e)}")
        return {} 