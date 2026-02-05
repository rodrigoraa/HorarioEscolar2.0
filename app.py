import streamlit as st
import pandas as pd
from xlsx_generator import gerar_modelo_excel
from data_manager import carregar_e_validar_dados
from engine import rodar_solver
from pdf_generator import gerar_pdf_bonito
from ui_renderer import desenhar_grade, exibir_carga_horaria
from auth import verificar_login
from auditor import auditoria_pre_solver
from exporters import gerar_excel_colorido

st.set_page_config(page_title="Gerar Horário Escolar", layout="wide")

logado, nome_usuario, authenticator = verificar_login()

if not logado:
    st.stop()
    
with st.sidebar:
    st.write(f"Olá, **{nome_usuario}**! 👋")
    authenticator.logout('Sair', 'sidebar')
    st.divider()

st.title("🧩 Gerador de Horários")

with st.expander("📥 Baixar Modelo de Planilha", expanded=False):
    col_dl1, col_dl2 = st.columns([1, 2])
    
    with col_dl1:
        st.markdown("### 1. Download")
        st.write("Baixe a planilha padrão:")
        
        excel_bytes = gerar_modelo_excel()
        
        st.download_button(
            label="💾 Baixar Modelo.xlsx",
            data=excel_bytes,
            file_name="modelo_horario_escolar.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col_dl2:
        st.markdown("### 2. Instruções Rápidas")
        st.info("""
        **Aba 'Turmas':** Coloque o nome da turma e total de aulas (25 ou 30).
        
        **Aba 'Grade_Curricular':**
        - **Turmas_Alvo:** Separe por vírgula se for para várias salas (Ex: `9A, 9B`).
        - **Indisponibilidade:** Dias que o prof NÃO pode (Ex: `Seg, Qua`) ou as aulas que o professor não pode dar (Ex: Seg:1, Ter:3).
        - **ATENÇÃO:** Mantenha um padrão para os nomes das turmas e dos professores para evitar erros na geração do horário.

        """)

arquivo = st.file_uploader("Upload da Planilha Excel", type=['xlsx'])

if arquivo:
    try:
        turmas_config, grade_aulas, erros, avisos = carregar_e_validar_dados(arquivo)
    except Exception as e:
        st.error(f"❌ Erro Crítico: O arquivo enviado é inválido ou está corrompido.")
        st.error(f"Detalhes: {str(e)}")
        st.stop()
    if erros:
        st.error("❌ Erros encontrados no arquivo:")
        for e in erros: st.write(f"- {e}")
        st.stop()
    if avisos:
        with st.expander("⚠️ Avisos e Ajustes Automáticos (Importante)", expanded=True):
            for a in avisos: st.write(f"- {a}")
        
    st.success("✅ Arquivo processado com sucesso!")

    qtd_professores = len(set([i['prof'] for i in grade_aulas]))
    qtd_disciplinas = len(set([i['materia'] for i in grade_aulas]))
    qtd_total_aulas = sum([i['qtd'] for i in grade_aulas])
    qtd_turmas = len(turmas_config)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    kpi1.metric("👨‍🏫 Professores", qtd_professores)
    kpi2.metric("🏫 Turmas", qtd_turmas)
    kpi3.metric("📚 Disciplinas", qtd_disciplinas)
    kpi4.metric("⏱️ Total de Aulas", qtd_total_aulas)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        dias = st.multiselect("Dias Letivos", 
                            ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab'], 
                            ['Seg', 'Ter', 'Qua', 'Qui', 'Sex'])
    with col2:
        st.info(f"Turmas detectadas: {len(turmas_config)}")
        
    with st.expander("🕒 Gestão de Hora Atividade (H.A.)", expanded=False):
        st.markdown("Defina a quantidade de aulas dedicadas a planejamento para cada professor.")
        
        lista_professores = sorted(list(set([i['prof'] for i in grade_aulas])))
        
        df_ha_inicial = pd.DataFrame({
            "Professor": lista_professores,
            "tem_ha": [False] * len(lista_professores),
            "qtd_aulas": [2] * len(lista_professores)
        })
        
        editor_ha = st.data_editor(
            df_ha_inicial,
            column_config={
                "tem_ha": st.column_config.CheckboxColumn(
                    "Tem Hora atividade?",
                    help="Marque se este professor tem direito a Hora Atividade na grade."
                ),
                "qtd_aulas": st.column_config.NumberColumn(
                    "Qtd Semanal",
                    min_value=1,
                    max_value=10,
                    step=1,
                    format="%d aulas"
                )
            },
            disabled=["Professor"],
            hide_index=True,
            use_container_width=True)

    with st.expander("⚙️ Configuração de Itinerários Formativos (Novo Ensino Médio)", expanded=False):
        st.markdown("Defina quais matérias são fixas e em quais horários elas devem ocorrer.")
        
        todas_materias = sorted(list(set([i['materia'] for i in grade_aulas])))
        
        itinerarios_selecionados = st.multiselect(
            "Quais disciplinas são Itinerários?", 
            todas_materias
        )
        
        slots_itinerario_user = st.multiselect(
            "Em quais aulas os itinerários ocorrem?",
            options=[1, 2, 3, 4, 5, 6],
            default=[6]
        )
        
        slots_itinerario_idx = [s-1 for s in slots_itinerario_user]
        
        if 'grupos_sincronia' not in st.session_state:
            st.session_state['grupos_sincronia'] = []

        with st.expander("🤝 Sincronia de Dias (Agrupar Matérias)", expanded=False):
            st.markdown("""
            **Como funciona:** Selecione matérias (ex: Robótica). O sistema forçará **TODAS** as turmas dessa matéria a terem aula no mesmo dia.
            *Útil para: Professores que atendem a escola toda no mesmo dia ou Projetos Interdisciplinares.*
            """)
            
            lista_materias = sorted(list(set([i['materia'] for i in grade_aulas])))
            
            selecao_materias = st.multiselect(
                "Quais matérias devem cair no mesmo dia?",
                options=lista_materias,
                placeholder="Ex: Robótica, Xadrez..."
            )
            
            c_btn1, c_btn2 = st.columns([1, 4])
            with c_btn1:
                if st.button("➕ Criar Grupo"):
                    if not selecao_materias:
                        st.warning("Selecione pelo menos 1 matéria.")
                    else:
                        st.session_state['grupos_sincronia'].append(selecao_materias)
                        st.success("Regra adicionada!")

            if st.session_state['grupos_sincronia']:
                st.divider()
                st.markdown("##### 🔗 Grupos Sincronizados:")
                for i, grupo in enumerate(st.session_state['grupos_sincronia']):
                    col_txt, col_del = st.columns([6, 1])
                    with col_txt:
                        st.info(f"**Grupo {i+1}:** {', '.join(grupo)}")
                    with col_del:
                        if st.button("🗑️", key=f"del_g_{i}"):
                            st.session_state['grupos_sincronia'].pop(i)
                            st.rerun()

    if 'horario_gerado' not in st.session_state:
        st.session_state['horario_gerado'] = False
        st.session_state['dados_solucao'] = {}

    st.markdown("### ⚙️ Preferências de Geração")
    
    usar_dobradinhas = st.toggle(
        "Permitir Dobradinhas (Aulas seguidas)?", 
        value=True,
        help="Ativado: Você pode escolher quem dobra. Desativado: O sistema tenta separar as aulas de TODOS os professores."
    )
    
    lista_todos_profs = sorted(list(set([i['prof'] for i in grade_aulas])))    
    
    if usar_dobradinhas:
        st.info("Selecione abaixo APENAS os professores que podem ter dobradinha.")
        profs_dobradinha = st.multiselect(
            "Quais professores podem dobrar?",
            options=lista_todos_profs,
            default=lista_todos_profs,
            help="Remova da lista quem você quer que tenha aulas separadas."
        )
    else:
        profs_dobradinha = []

    if st.button("🚀 Gerar Horário (Modo Blindado)"):
        
        with st.spinner("Preparando resultados. . ."):
            
            turmas_final = turmas_config.copy()
            grade_final = grade_aulas.copy()

            if 'editor_ha' in locals() and editor_ha is not None:
                profs_com_ha = editor_ha[editor_ha["tem_ha"] == True]
                
                for _, row in profs_com_ha.iterrows():
                    prof_nome = row["Professor"]
                    qtd_ha = row["qtd_aulas"]
                    
                    turma_fantasma = f"H.A. ({prof_nome})"
                    turmas_final[turma_fantasma] = 25
                    
                    grade_final.append({
                        'id_linha': 9999,
                        'prof': prof_nome,
                        'materia': 'Hora Atividade',
                        'turma': turma_fantasma,
                        'qtd': int(qtd_ha),
                        'bloqueios_indices': []
                    })

            erros_mat, avisos_mat = auditoria_pre_solver(grade_aulas, turmas_config, dias)
            
        if erros_mat:
            st.error("❌ Matemática Impossível (Carga horária excede os espaços disponíveis):")
            for em in erros_mat:
                st.write(f"- {em}")
                st.session_state['horario_gerado'] = False
                st.stop()
        if avisos_mat:
            with st.expander("⚠️ Alertas de Capacidade", expanded=True):
                for am in avisos_mat:
                    st.write(f"- {am}")

        with st.spinner("Calculando a melhor solução possível. . ."):
            regras_projeto = st.session_state.get('regras_projetos', [])

            status, resultados, slots_dia = rodar_solver(
                turmas_final,           
                grade_final,            
                dias,
                itinerarios_selecionados,
                slots_itinerario_idx,
                st.session_state['grupos_sincronia'],
                professores_com_dobradinha=profs_dobradinha
            )
                
            if status == "SUCESSO":
                st.session_state['horario_gerado'] = True
                st.session_state['dados_solucao'] = {
                    'resultados': resultados,
                    'turmas_final': turmas_final,
                    'slots_dia': slots_dia,
                    'dias_selecionados': dias
                }
                st.success("✅ Horário Gerado com Sucesso!")
            else:
                st.session_state['horario_gerado'] = False
                st.error("❌ Não foi possível gerar o horário com as configurações atuais.")
    
    if st.session_state['horario_gerado']:
        
        dados = st.session_state['dados_solucao']
        res = dados['resultados']
        turmas_f = dados['turmas_final']
        d_sel = dados['dias_selecionados']
        s_dia = dados['slots_dia']
                
        exibir_carga_horaria(res, d_sel)
        desenhar_grade(res, d_sel, s_dia)
                
        st.divider()
        st.markdown("### 📥 Baixar Arquivos")
                
        col_pdf, col_xls = st.columns(2)
        
        with col_pdf:
            pdf_bytes = gerar_pdf_bonito(res, turmas_f, d_sel)
            st.download_button(
                label="📄 Baixar Horário em PDF",
                data=pdf_bytes,
                file_name="horario_escolar.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        with col_xls:
            xls_bytes = gerar_excel_colorido(res, d_sel)
            st.download_button(
                label="📊 Baixar Excel para edição",
                data=xls_bytes,
                file_name="horario_editar.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )