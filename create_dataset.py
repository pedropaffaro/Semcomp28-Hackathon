import pandas as pd
from faker import Faker
import random

fake = Faker('pt_BR')

n = 10000
categorias = ["alimentação", "transporte", "despesas pessoais", "educação",
              "casa", "saúde", "lazer", "comunicação", "outros"]
formas_pagamento = ["pix", "cartão débito", "cartão crédito", "boleto"]


dados_estabelecimentos = {
    "alimentação": {
        "Padaria": (5, 70),
        "Lanchonete": (8, 80),
        "Cafeteria": (5, 60),
        "Sorveteria": (5, 50),
        "Doceria": (10, 70),
        "Restaurante": (20, 300),
        "Açougue": (20, 200),
        "Hortifruti": (15, 150),
        "Mercado": (30, 400),        
        "Supermercado": (100, 1200), 
    },
    "transporte": {
        "Posto de Gasolina": (30, 250),
        "App de Transporte": (10, 70),
        "Metrô": (5, 50),
        "Empresa de Ônibus": (10, 100),
        "Pedágio": (5, 80),
        "Estacionamento": (10, 150),
        "Loja de Peças": (50, 1000),
        "Oficina Mecânica": (100, 3000),
    },
    "despesas pessoais": {
        "Salão de Beleza": (30, 300),
        "Barbearia": (20, 100),
        "Perfumaria": (50, 500),
        "Loja de Roupas": (50, 800),
        "Loja de Calçados": (70, 600),
        "Livraria": (20, 300), 
        "Academia": (80, 250),
        "Pet Shop": (30, 400),
    },
    "educação": {
        "Papelaria": (5, 150),
        "Livraria": (30, 400),
        "Curso Online": (50, 1000),
        "Curso de Idiomas": (200, 800),
        "Escola": (500, 3000),
        "Faculdade": (800, 5000),
    },
    "casa": {
        "Loja de Móveis": (200, 5000),
        "Material de Construção": (50, 5000),
        "Loja de Decoração": (30, 700),
        "Loja de Utilidades": (10, 200),
        "Eletricista": (100, 1000),
        "Conta de Luz": (80, 500),
        "Conta de Água": (50, 300),
        "Aluguel": (800, 4000),
    },
    "saúde": {
        "Farmácia": (10, 300),
        "Laboratório": (100, 800),
        "Consultório Médico": (150, 600),
        "Clínica Odontológica": (100, 1500),
        "Plano de Saúde": (300, 2000),
        "Hospital": (200, 5000),
    },
    "lazer": {
        "Bar": (30, 250),
        "Cinema": (20, 100),
        "Teatro": (50, 300),
        "Show": (100, 800),
        "Parque": (10, 100),
        "Streaming": (20, 60),
        "Loja de Jogos": (50, 500),
        "Agência de Viagens": (500, 5000),
    },
    "comunicação": {
        "Recarga de Celular": (15, 100),
        "Companhia Telefônica": (50, 250),
        "Provedor de Internet": (80, 300),
        "Serviços Postais": (5, 50),
    },
    "outros": {
        "Loja de Departamentos": (20, 500),
        "Serviços Gerais": (50, 1000),
        "Doação": (10, 500),
        "Impostos": (100, 2000),
        "Consultoria": (200, 3000),
    }
}

categorias_lista = []
destinatarios_lista = []
valores_lista = []

for _ in range(n):
    cat_escolhida = random.choice(categorias)
    categorias_lista.append(cat_escolhida)

    opcoes_estab = dados_estabelecimentos[cat_escolhida]
    lista_tipos_estab = list(opcoes_estab.keys())
    
    tipo_estab_escolhido = random.choice(lista_tipos_estab)

    nome_empresa = fake.company()
    destinatario_final = f"{tipo_estab_escolhido} {nome_empresa}".strip()
    destinatarios_lista.append(destinatario_final)
    
    min_val, max_val = opcoes_estab[tipo_estab_escolhido]
    
    valor = round(random.uniform(min_val, max_val), 2)
    valores_lista.append(valor)

data = {
    "id_transacao": range(1, n + 1),
    "data": [fake.date_between(start_date='-20y', end_date='today') for _ in range(n)],
    "hora": [fake.time(pattern="%H:%M:%S") for _ in range(n)],
    "destinatario": destinatarios_lista,  
    "valor": valores_lista,              
    "categoria": categorias_lista,       
    "forma_pagamento": [random.choice(formas_pagamento) for _ in range(n)]
}

df = pd.DataFrame(data)

df.to_csv("transacoes_bancarias.csv", index=False, encoding="utf-8")

print("✅ Dataset 'transacoes_bancarias.csv' gerado com sucesso!")
print("\nExemplo do DataFrame (note a correlação entre destinatário e valor):")
print(df.head(15))