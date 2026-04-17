import asyncio
import functions_framework
import os
from pybyd import BydClient, BydConfig

class ExtendedBydConfig(BydConfig):
    country_code: str = "BR"
    language: str = "pt-BR"
    base_url: str = "https://dilinkappoversea-br.byd.auto"
    time_zone: str = "America/Sao_Paulo"

# Verificação de porta para o log
port = os.environ.get("PORT", "8080")
print(f"Iniciando servidor na porta {port}...")

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
            return "Nenhum veículo encontrado."

        vin = vehicles[0].vin
        realtime = await client.get_vehicle_realtime(vin)
        
        # O retorno aqui será o que aparecerá no seu navegador
        resultado = (
            f"VIN: {vin} | "
            f"Bateria: {realtime.elec_percent}% | "
            f"Autonomia: {realtime.endurance_mileage} km"
        )
        return resultado
