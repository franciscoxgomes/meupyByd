import asyncio
import functions_framework
import os
import json
from datetime import datetime, timezone
from pybyd import BydClient, BydConfig
from dotenv import load_dotenv
from gera_template import funcaoTemplate
if not os.environ.get("BYD_USERNAME", None):
  load_dotenv() # Isso carrega as variáveis do arquivo .env
 
    

class ExtendedBydConfig(BydConfig):
    country_code: str = "BR"
    language: str = "pt-BR"
    base_url: str = "https://dilinkappoversea-br.byd.auto"
    time_zone: str = "America/Sao_Paulo"

#
@functions_framework.http
def hello_byd(request):
    # O loop do asyncio deve rodar aqui dentro
    return asyncio.run(fetch_byd_data())
    
async def fetch_byd_data():
    config = ExtendedBydConfig(
        username=os.environ.get("BYD_USERNAME"),
        password=os.environ.get("BYD_PASSWORD"),
    )

    async with BydClient(config) as client:
        vehicles = await client.get_vehicles()
        if not vehicles:
            html = "<html><body><p>Nenhum veículo encontrado.</p></body></html>"
            return (html, 200, {"Content-Type": "text/html; charset=utf-8"})

        vin = vehicles[0].vin
        realtime = await client.get_vehicle_realtime(vin)
       
        # Monta um objeto "data" compatível com o template JS (reduzido ao necessário)
        
        data = {
            "userId": os.environ.get("BYD_USER_ID", ""),
            "vin": vin,
            "vehicles": [
                {
                    "vin": vin,
                    "modelName": getattr(vehicles[0], "modelName", "") if hasattr(vehicles[0], "modelName") else "",
                    "autoAlias": getattr(vehicles[0], "autoAlias", "") if hasattr(vehicles[0], "autoAlias") else "",
                    "autoPlate": getattr(vehicles[0], "autoPlate", "") if hasattr(vehicles[0], "autoPlate") else "",
                    "brandName": getattr(vehicles[0], "brandName", "") if hasattr(vehicles[0], "brandName") else "BYD",
                    "totalMileage": getattr(vehicles[0], "total_mileage", None),
                }
            ],
            "vehicleInfo": realtime.raw if hasattr(realtime, "raw") else {},
            "gps": {"ok": False, "message": "", "gpsInfo": None},
        }
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 

        # HTML template (o conteúdo fornecido pelo usuário) com placeholders:
        html_template = funcaoTemplate(data,generated_at)       
        # Insere JSON e timestamp no template. json.dumps produz conteúdo JS válido.
        safe_json = json.dumps(data, ensure_ascii=False)
        html = html_template.replace('PLACEHOLDER_DATA', safe_json).replace('PLACEHOLDER_GENERATED_AT', generated_at)

        # Retorna HTML com header adequado
        return (html, 200, {"Content-Type": "text/html; charset=utf-8"})




if __name__ == "__main__":
    # Roda a função de busca de dados e imprime o resultado no terminal
    print("Executando busca de dados localmente...")
    try:
        resultado_local = asyncio.run(fetch_byd_data())
        # resultado_local é uma tupla (html, status, headers)
        html_text = resultado_local[0] if isinstance(resultado_local, tuple) else resultado_local
        with open("output.html", "w", encoding="utf-8") as f:
            f.write(html_text)  
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")