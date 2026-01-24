from ortools.sat.python import cp_model
from collections import defaultdict

def rodar_solver(turmas_config, grade_aulas, dias_semana, itinerarios_lista=[], slots_itinerario_perm=[], agrupamentos_projetos=[]):
    
    print(">>> Iniciando Solver com Projetos Interdisciplinares...")
    model = cp_model.CpModel()
    qtd_dias = len(dias_semana)

    # Variáveis
    horario = {} 
    vars_list = defaultdict(list)
    custo_total = [] 

    # Dicionário auxiliar para acesso rápido às variáveis por (turma, materia, dia)
    # Estrutura: mapa_vars[turma][materia][dia] = [lista de variáveis booleans dos slots]
    mapa_vars = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    def get_slots_da_turma(nome_turma):
        carga = turmas_config.get(nome_turma, 25)
        if carga > 25: return 6
        return 5

    # --- 1. CRIAÇÃO DAS VARIÁVEIS ---
    for item in grade_aulas:
        t, p, m, q = item['turma'], item['prof'], item['materia'], item['qtd']
        bloqueios = item.get('bloqueios_indices', []) 
        
        slots_desta_turma = get_slots_da_turma(t)
        eh_itinerario = (m in itinerarios_lista)

        for d in range(qtd_dias):
            for a in range(slots_desta_turma):
                v = model.NewBoolVar(f"H_{t}_{p}_{m}_{d}_{a}")
                horario[(t, d, a, p, m)] = v
                
                # Guarda referência para usar nas regras de projeto depois
                mapa_vars[t][m][d].append(v)

                # Regras de bloqueio e itinerário
                if d in bloqueios: model.Add(v == 0)
                if eh_itinerario and slots_itinerario_perm:
                    if a not in slots_itinerario_perm: model.Add(v == 0)

                vars_list['turma_slot'].append(((t, d, a), v))
                vars_list['prof_slot'].append(((p, d, a), v))
                vars_list['item_total'].append(((t, p, m), v))
                vars_list[f'prof_turma_dia_{t}_{p}_{d}'].append(v)

    # --- 2. REGRAS GERAIS (Lógica do Motor) ---

    # [Restrição A] Carga Horária Exata
    # Garante que se a matéria pede 4 aulas, ela terá exatamente 4 aulas na semana.
    processed_items = set()
    for item in grade_aulas:
        key = (item['turma'], item['prof'], item['materia'])
        if key in processed_items: continue
        processed_items.add(key)
        
        # Pega todas as variáveis dessa matéria específica
        vars_dessa_materia = [v for (k, v) in vars_list['item_total'] if k == key]
        model.Add(sum(vars_dessa_materia) == item['qtd'])

    # [Restrição B] Choque de Turma (1 Prof por Turma/Slot)
    # Uma turma não pode ter dois professores ao mesmo tempo.
    slots_map = defaultdict(list)
    for (t, d, a), v in vars_list['turma_slot']:
        slots_map[(t, d, a)].append(v)
    for slot_vars in slots_map.values():
        model.Add(sum(slot_vars) <= 1)

    # [Restrição C] Choque de Professor (1 Turma por Prof/Slot)
    # Um professor não pode estar em duas turmas ao mesmo tempo.
    prof_slots_map = defaultdict(list)
    for (p, d, a), v in vars_list['prof_slot']:
        prof_slots_map[(p, d, a)].append(v)
    for slot_vars in prof_slots_map.values():
        model.Add(sum(slot_vars) <= 1)

    # [Restrição D] Qualidade: Evitar Janelas e Buracos
    # Tenta agrupar as aulas do professor para ele não ficar indo e voltando.
    for key, vars_dia in vars_list.items():
        if key.startswith('prof_turma_dia_'):
            parts = key.split('_')
            t_nome = parts[3] # Nome da turma
            slots_desta_turma = get_slots_da_turma(t_nome)
            
            soma_hoje = model.NewIntVar(0, slots_desta_turma, f"soma_{key}")
            model.Add(sum(vars_dia) == soma_hoje)
            
            # Penaliza aulas espalhadas (Ex: aula na 1ª e na 5ª)
            # A matemática aqui penaliza "buracos" elevando ao quadrado
            quadrado = model.NewIntVar(0, slots_desta_turma**2, f"sq_{key}")
            model.AddMultiplicationEquality(quadrado, [soma_hoje, soma_hoje])
            custo_total.append(quadrado * 10) 

    # [Restrição E] Máximo de aulas diárias por matéria
    # Impede que uma turma tenha, por exemplo, 4 aulas de Matemática no mesmo dia.
    # O ideal pedagógico é no máximo 2 aulas dobradinhas.
    for t in mapa_vars:
        for m in mapa_vars[t]:
            # Pula se for itinerário, pois itinerário pode ter tarde toda
            if m in itinerarios_lista:
                continue
                
            for d in range(qtd_dias):
                aulas_no_dia = mapa_vars[t][m][d]
                if aulas_no_dia:
                    # Limite Hard: Máximo 2 aulas da mesma matéria por dia
                    model.Add(sum(aulas_no_dia) <= 2)

    # --- 3.REGRAS DE PROJETOS (CONCOMITÂNCIA) ---
    # Lógica: Se a 'materia_ancora' (menor qtd) tem aula no dia D, 
    # as 'materias_parceiras' TAMBÉM devem ter aula no dia D.
    
    if agrupamentos_projetos:
        print(f"> Processando {len(agrupamentos_projetos)} grupos de sincronia global...")
        
        for lista_nomes_materias in agrupamentos_projetos:
            
            # 1. Encontrar TODAS as ocorrências dessas matérias em TODAS as turmas
            itens_afetados = []
            for item in grade_aulas:
                if item['materia'] in lista_nomes_materias:
                    itens_afetados.append(item)
            
            if not itens_afetados:
                continue

            # 2. Ordenar pelo que tem MENOS aulas (será o Pivô/Líder)
            # Ex: Se Robótica 6A tem 2 aulas e Robótica 9B tem 2 aulas, qualquer um serve.
            # Se Arte tem 1 aula e Música tem 2, Arte manda (quem tem menos restringe mais).
            itens_afetados.sort(key=lambda x: x['qtd'])
            
            pivo = itens_afetados[0]
            satelites = itens_afetados[1:]
            
            print(f"  -> Grupo Sincronia ({lista_nomes_materias}): Pivô é {pivo['materia']} da turma {pivo['turma']}")
            
            for d in range(qtd_dias):
                # Variável: O Pivô está presente no dia D?
                # (Acessa o mapa_vars criado no início da função)
                slots_pivo = mapa_vars[pivo['turma']][pivo['materia']][d]
                if not slots_pivo: continue 

                pivo_presente = model.NewBoolVar(f"sync_pivo_{d}_{pivo['id_linha']}")
                model.Add(sum(slots_pivo) > 0).OnlyEnforceIf(pivo_presente)
                model.Add(sum(slots_pivo) == 0).OnlyEnforceIf(pivo_presente.Not())
                
                # Amarra todos os outros (satélites) ao Pivô
                for sat in satelites:
                    slots_sat = mapa_vars[sat['turma']][sat['materia']][d]
                    if not slots_sat: continue
                    
                    sat_presente = model.NewBoolVar(f"sync_sat_{d}_{sat['id_linha']}")
                    model.Add(sum(slots_sat) > 0).OnlyEnforceIf(sat_presente)
                    model.Add(sum(slots_sat) == 0).OnlyEnforceIf(sat_presente.Not())
                    
                    # REGRA DE IMPLICAÇÃO:
                    # Se o Pivô tem aula hoje -> O Satélite TAMBÉM tem que ter.
                    model.AddImplication(pivo_presente, sat_presente)
                    
                    # Se as cargas horárias forem idênticas (ex: ambos 2 aulas),
                    # força a igualdade total (se um não vai, o outro também não).
                    if sat['qtd'] == pivo['qtd']:
                         model.Add(pivo_presente == sat_presente)

    # --- SOLVER ---
    model.Minimize(sum(custo_total))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60
    
    status = solver.Solve(model)
    
    resultado_final = []
    
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        for (t, d, a, p, m), v in horario.items():
            if solver.Value(v) == 1:
                resultado_final.append({
                    'turma': t,
                    'dia_idx': d,
                    'aula_idx': a,
                    'prof': p,
                    'materia': m
                })
        return "SUCESSO", resultado_final, get_slots_da_turma
    else:
        return "FALHA", [], get_slots_da_turma