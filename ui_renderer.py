import streamlit as st
import pandas as pd

def desenhar_grade(resultados, dias_semana, _ignored=None):
    if not resultados:
        st.warning("Sem resultados para exibir.")
        return

    df = pd.DataFrame(resultados)
    turmas = sorted(df['turma'].unique())

    for turma in turmas:
        st.markdown(f"### 🏫 Turma: {turma}")
        
        # Filtra dados da turma
        df_t = df[df['turma'] == turma]
        
        # Descobre automaticamente o tamanho da tabela desta turma
        # Se houver alguma aula na 6ª posição (índice 5), a tabela terá 6 linhas.
        max_aula_idx = df_t['aula_idx'].max()
        
        # Se for fundamental (geralmente max index é 4), mostramos 5 aulas.
        # Se for médio (tem aula no index 5), mostramos 6.
        # Por segurança, garante no mínimo 5 aulas.
        qtd_aulas_visual = max(5, int(max_aula_idx) + 1)
        
        grid = {d: ["---"] * qtd_aulas_visual for d in dias_semana}
        
        for _, row in df_t.iterrows():
            d_nome = dias_semana[row['dia_idx']]
            a_idx = row['aula_idx']
            texto = f"{row['materia']}\n({row['prof']})"
            
            if a_idx < qtd_aulas_visual:
                grid[d_nome][a_idx] = texto
                
        # Exibe
        df_visual = pd.DataFrame(grid)
        df_visual.index = [f"{i+1}ª Aula" for i in range(qtd_aulas_visual)]
        st.table(df_visual)
        st.markdown("---")

def exibir_carga_horaria(resultados, dias_semana):
    """
    Exibe tabela com contagem de aulas (Heatmap) e Total Semanal.
    """
    if not resultados:
        return

    st.markdown("### 📊 Carga Horária e Distribuição")

    # 1. Cria o DataFrame base
    df = pd.DataFrame(resultados)
    
    # 2. Pivot Table (Linhas: Prof | Colunas: Dias | Valores: Contagem)
    df_pivot = df.pivot_table(
        index='prof', 
        columns='dia_idx', 
        values='turma', 
        aggfunc='count', 
        fill_value=0
    )

    # 3. Garante colunas para todos os dias (0 a N-1)
    todos_indices = range(len(dias_semana))
    df_pivot = df_pivot.reindex(columns=todos_indices, fill_value=0)

    # 4. Renomeia 0,1,2 -> Seg, Ter, Qua
    mapa_dias = {i: nome for i, nome in enumerate(dias_semana)}
    df_pivot.rename(columns=mapa_dias, inplace=True)

    # 5. Coluna TOTAL
    df_pivot['TOTAL'] = df_pivot.sum(axis=1)

    # 6. Exibe com DOIS gradientes de cor
    # - Reds (Vermelho) para os dias (alerta de dia cheio)
    # - Blues (Azul) para o Total (alerta de carga semanal)
    st.dataframe(
        df_pivot.style
        .background_gradient(cmap='Reds', subset=dias_semana) # Calor nos dias
        .background_gradient(cmap='Blues', subset=['TOTAL'])  # Destaque no total
        .format("{:.0f}"), # Remove decimais
        use_container_width=True
    )