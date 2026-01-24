def auditoria_pre_solver(grade_aulas, turmas_config, dias_list):
    """
    Verifica se a quantidade de aulas solicitadas cabe na semana.
    Retorna listas de erros (impeditivos) e avisos (alertas).
    """
    erros = []
    avisos = []
    
    # Define o limite máximo de slots (ex: 5 dias * 5 aulas = 25)
    # Se permitir 6ª aula, o limite seria 30. Usa uma margem segura.
    slots_por_dia = 6 # Margem para evitar falsos positivos se tiver 6ª aula
    max_slots_semana = len(dias_list) * slots_por_dia
    
    # 1. Checagem de Professores
    carga_prof = {}
    for item in grade_aulas:
        p = item['prof']
        carga_prof[p] = carga_prof.get(p, 0) + item['qtd']
    
    for prof, qtd in carga_prof.items():
        if qtd > max_slots_semana:
            erros.append(f"❌ O Prof. **{prof}** tem {qtd} aulas atribuídas, mas a semana só tem {max_slots_semana} espaços possíveis.")

    # 2. Checagem de Turmas
    carga_turma = {}
    for item in grade_aulas:
        t = item['turma']
        carga_turma[t] = carga_turma.get(t, 0) + item['qtd']
        
    for turma, qtd in carga_turma.items():
        limite_turma = turmas_config.get(turma, 25)
        if qtd > limite_turma + 2: # +2 de tolerância
            erros.append(f"❌ A turma **{turma}** tem {qtd} aulas cadastradas, mas o limite configurado é próximo de {limite_turma}.")
            
    return erros, avisos