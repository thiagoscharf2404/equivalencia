import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, ArrowDownToLine, ArrowLeft, ArrowRight, Building2, Check, CheckCircle2,
  ChevronDown, CircleHelp, Clock3, FileCheck2, FileText, GraduationCap,
  LayoutDashboard, ListChecks, LoaderCircle, Menu, Plus, Search,
  Settings2, ShieldCheck, Sparkles, Upload, UserRound, X, LogOut, LockKeyhole, Mail,
} from "lucide-react";
import {
  createAnalysis, decideSuggestion, downloadReport, extractHistory,
  createStudent, getAnalysis, getAnalyses, getCourses, getMatrices, requestAiAnalysis,
  searchStudents, updateStudent, addManualSuggestion, getCandidates,
  saveHistoryReview, getSession, getUnits, login, logout,
} from "./api";

const steps = [
  ["Aluno", "Identificação do aluno"],
  ["Origem do aproveitamento", "Instituição e curso de origem"],
  ["Destino", "Curso e matriz da universidade"],
  ["Documentos", "Histórico e planos de ensino"],
  ["Análise", "Leitura e comparação"],
  ["Revisão", "Decisão do coordenador"],
  ["Resultado", "Documento de aproveitamento"],
];

const emptyForm = {
  student_id: "", student_name: "", student_ra: "", origin_institution: "", origin_course: "",
  origin_status: "", target_course_id: "", target_matrix_id: "", term: "",
  history: null, plans: [],
};

function LoginPage({ onLogin }) {
  const [units, setUnits] = useState([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [unitId, setUnitId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { getUnits().then((items) => { setUnits(items); if (items.length) setUnitId(String(items[0].id)); }).catch((e) => setError(e.message)); }, []);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError("");
    try { await onLogin({ email: email.trim(), password, unit_id: Number(unitId) }); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  return <main className="login-page">
    <section className="login-brand-panel"><div className="login-brand"><span className="brand-mark"><GraduationCap size={23} /></span><span>equivalenc<span className="brand-accent">IA</span></span></div>
      <div className="login-story"><span className="login-eyebrow"><Sparkles size={14} /> GESTÃO ACADÊMICA</span><h1>Equivalências com clareza, do início ao parecer.</h1><p>Um espaço de trabalho para a coordenação organizar documentos, revisar evidências e acompanhar cada análise.</p>
        <div className="login-flow"><span>Cadastro</span><i /><span>Análise</span><i /><span>Revisão</span><i /><span>Parecer</span></div>
      </div><small className="login-footer">Ambiente institucional · Acesso restrito à coordenação</small>
    </section>
    <section className="login-form-panel"><form className="login-card" onSubmit={submit}>
      <span className="login-form-icon"><LockKeyhole size={19} /></span><div className="eyebrow">BEM-VINDA(O) DE VOLTA</div><h2>Entrar na coordenação</h2><p>Use seu e-mail institucional para continuar.</p>
      {error && <div className="login-error" role="alert">{error}</div>}
      <label className="login-field"><span>Unidade / campus</span><span className="login-input"><Building2 size={16} /><select value={unitId} onChange={(e) => setUnitId(e.target.value)} required disabled={!units.length}><option value="">{units.length ? "Selecione sua unidade" : "Nenhuma unidade disponível"}</option>{units.map((unit) => <option value={unit.id} key={unit.id}>{unit.name}</option>)}</select></span></label>
      <label className="login-field"><span>E-mail institucional</span><span className="login-input"><Mail size={16} /><input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nome@instituicao.edu.br" required /></span></label>
      <label className="login-field"><span>Senha</span><span className="login-input"><LockKeyhole size={16} /><input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Digite sua senha" required /></span></label>
      <button className="button button-primary login-submit" disabled={busy || !unitId}>{busy ? <LoaderCircle className="spin" size={16} /> : <LockKeyhole size={16} />} Entrar</button>
      <div className="login-secure"><ShieldCheck size={14} /> Sessão protegida · seus dados ficam associados à unidade selecionada</div>
    </form><small className="login-help">Problemas para acessar? Procure o administrador do sistema.</small></section>
  </main>;
}

function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [screen, setScreen] = useState("home");
  const [analyses, setAnalyses] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [step, setStep] = useState(0);
  const [form, setForm] = useState(emptyForm);
  const [courses, setCourses] = useState([]);
  const [students, setStudents] = useState([]);
  const [matrices, setMatrices] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [studentSearch, setStudentSearch] = useState("");
  const [showRegisterStudent, setShowRegisterStudent] = useState(false);
  const [editingStudent, setEditingStudent] = useState(null);
  const [registerBusy, setRegisterBusy] = useState(false);
  const [coordinatorNote, setCoordinatorNote] = useState("");

  useEffect(() => {
    if (!error) return undefined;
    const timeoutId = window.setTimeout(() => setError(""), 5000);
    return () => window.clearTimeout(timeoutId);
  }, [error]);

  useEffect(() => {
    if (!notice) return undefined;
    const timeoutId = window.setTimeout(() => setNotice(""), 5000);
    return () => window.clearTimeout(timeoutId);
  }, [notice]);

  const refresh = async () => {
    try { setAnalyses(await getAnalyses()); } catch (e) { setError(e.message); }
  };
  useEffect(() => { getSession().then(setUser).catch(() => {}).finally(() => setAuthChecked(true)); }, []);
  useEffect(() => { if (user) { refresh(); getCourses().then(setCourses).catch(() => {}); searchStudents("").then(setStudents).catch(() => {}); } }, [user]);
  useEffect(() => { if (user) searchStudents(studentSearch).then(setStudents).catch(() => {}); }, [studentSearch, user]);
  useEffect(() => {
    if (user && form.target_course_id) getMatrices(form.target_course_id).then(setMatrices).catch((e) => setError(e.message));
    else setMatrices([]);
  }, [form.target_course_id, user]);

  async function signIn(credentials) {
    await login(credentials);
    setUser(await getSession());
  }
  async function signOut() {
    await logout();
    setUser(null);
    setAnalyses([]);
    setCourses([]);
    setStudents([]);
  }

  const filtered = useMemo(() => analyses.filter((item) =>
    (item.student_name + " " + item.origin_course + " " + item.id)
      .toLowerCase().includes(search.toLowerCase())), [analyses, search]);

  function change(key, value) { setForm((current) => ({ ...current, [key]: value })); }
  function openNew() {
    setForm(emptyForm); setStep(0); setActiveId(null); setAnalysis(null);
    setStudentSearch(""); setShowRegisterStudent(false); setError(""); setNotice(""); setScreen("wizard");
  }
  async function registerStudent() {
    if (!form.student_name.trim()) return setError("O nome do aluno é obrigatório.");
    setRegisterBusy(true); setError("");
    try {
      const student = await createStudent({ name: form.student_name.trim(), ra: form.student_ra.trim() });
      setForm((current) => ({ ...current, student_id: String(student.id), student_name: student.name, student_ra: student.ra || "" }));
      setStudents((current) => [student, ...current.filter((item) => item.id !== student.id)]);
      setShowRegisterStudent(false);
      setNotice("Cadastro do aluno salvo. Ele poderá ser usado em outras análises.");
    } catch (e) { setError(e.message); }
    finally { setRegisterBusy(false); }
  }
  async function saveStudentEdit() {
    if (!editingStudent?.name.trim()) return setError("O nome do aluno é obrigatório.");
    setRegisterBusy(true); setError("");
    try {
      const updated = await updateStudent(editingStudent.id, {
        name: editingStudent.name.trim(), ra: editingStudent.ra.trim(),
      });
      setStudents((current) => current.map((item) => item.id === updated.id ? updated : item));
      if (String(updated.id) === form.student_id) {
        setForm((current) => ({ ...current, student_name: updated.name, student_ra: updated.ra || "" }));
      }
      setEditingStudent(null); setNotice("Cadastro do aluno atualizado.");
    } catch (e) { setError(e.message); }
    finally { setRegisterBusy(false); }
  }
  async function openAnalysis(id) {
    setBusy(true); setError("");
    try {
      const data = await getAnalysis(id);
      setActiveId(id); setAnalysis(data);
      setStep(data.suggestions?.length ? (data.suggestions.every((s) => s.decision !== "pending") ? 6 : 5) : 4);
      setScreen("wizard");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function continueStep() {
    setError(""); setNotice("");
    if (step === 0 && !form.student_id) return setError("Selecione ou cadastre o aluno antes de iniciar a análise.");
    if (step === 1 && (!form.origin_course || !form.origin_institution || !form.origin_status))
      return setError("Preencha instituição, curso e situação de origem.");
    if (step === 2 && (!form.target_course_id || !form.target_matrix_id))
      return setError("Selecione o curso e a matriz de destino.");
    if (step === 3) {
      if (!form.history) return setError("Anexe o histórico acadêmico para iniciar.");
      setBusy(true);
      try {
        const created = await createAnalysis(form);
        setActiveId(created.analysis_id);
        setAnalysis(created);
        setStep(4);
        setNotice("Solicitação registrada. Agora a extração pode ser iniciada.");
        await refresh();
      } catch (e) { setError(e.message); }
      finally { setBusy(false); }
      return;
    }
    setStep((n) => Math.min(n + 1, 6));
  }
  async function runExtraction() {
    setBusy(true); setError(""); setNotice("");
    try { setAnalysis(await extractHistory(activeId)); setNotice("Histórico lido. Confira os dados antes de continuar."); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function runAi() {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await requestAiAnalysis(activeId);
      setAnalysis((a) => ({ ...a, suggestions: result.suggestions, ai_analysis_done: true }));
      setStep(5);
      if (result.ai_configured === false) setNotice(result.message);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function saveDecision(suggestionId, decision) {
    try {
      await decideSuggestion(activeId, suggestionId, decision, "");
      setAnalysis(await getAnalysis(activeId));
      setNotice("Decisão do coordenador salva.");
    } catch (e) { setError(e.message); }
  }
  async function makeReport() {
    setBusy(true); setError("");
    try {
      const blob = await downloadReport(activeId, coordinatorNote);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url; link.download = "parecer-aproveitamento-" + activeId + ".docx";
      link.click(); URL.revokeObjectURL(url);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  if (!authChecked) return <div className="auth-loading"><div className="brand-mark"><GraduationCap size={22} /></div><LoaderCircle className="spin" size={18} /> Carregando área da coordenação…</div>;
  if (!user) return <LoginPage onLogin={signIn} />;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><GraduationCap size={22} /></div><span>equivalenc<span className="brand-accent">IA</span></span></div>
        <div className="workspace-label">{user.unit_name} <ChevronDown size={14} /></div>
        <div className="nav-group-label">ESPAÇO DE TRABALHO</div>
        <button className={"nav-item " + (screen === "home" ? "active" : "")} onClick={() => { setScreen("home"); setError(""); }}>
          <LayoutDashboard size={17} /> Visão geral
        </button>
        <button className={"nav-item " + (screen === "list" ? "active" : "")} onClick={() => setScreen("list")}>
          <ListChecks size={17} /> Análises <span className="nav-count">{analyses.length}</span>
        </button>
        <button className={"nav-item " + (screen === "students" ? "active" : "")} onClick={() => setScreen("students")}><UserRound size={17} /> Alunos</button>
        <button className="nav-item" onClick={openNew}><Plus size={17} /> Nova análise</button>
        <div className="sidebar-bottom">
          <div className="help-card"><div className="help-icon"><CircleHelp size={17} /></div><strong>Precisa de ajuda?</strong><span>Consulte o guia do coordenador</span><button>Ver guia <ArrowRight size={13} /></button></div>
          <div className="profile"><div className="avatar"><UserRound size={15} /></div><div className="profile-text"><strong>{user.name}</strong><span>{user.email}</span></div><button className="logout-button" title="Sair" onClick={signOut}><LogOut size={16} /></button></div>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs"><span>Coordenação</span><span className="crumb-slash">/</span><strong>{screen === "wizard" ? (activeId ? "Análise " + activeId : "Nova análise") : screen === "list" ? "Análises" : "Visão geral"}</strong></div>
          <div className="topbar-actions"><span className="secure-tag"><ShieldCheck size={14} /> Área da coordenação</span><button className="icon-button" title="Sair" onClick={signOut}><LogOut size={16} /></button></div>
        </header>
        {error && <div className="toast toast-error"><X size={16} />{error}<button onClick={() => setError("")}><X size={15} /></button></div>}
        {notice && <div className="toast toast-success"><CheckCircle2 size={16} />{notice}<button onClick={() => setNotice("")}><X size={15} /></button></div>}
        {screen === "wizard" ? (
          <section className="content wizard-content">
            <div className="page-heading"><div><div className="eyebrow">FLUXO DE APROVEITAMENTO</div><h1>{activeId ? "Análise de aproveitamento" : "Nova análise"}</h1><p>Preencha os dados do aluno e prepare o processo para revisão da coordenação.</p></div>
              <button className="button button-quiet" onClick={() => { setScreen("home"); setError(""); }}><X size={16} /> Fechar</button>
            </div>
            <div className="wizard-layout">
              <nav className="step-rail" aria-label="Etapas da análise">
                {steps.map((item, index) => <button key={item[0]} onClick={() => index < step && setStep(index)} disabled={index > step} className={"rail-step " + (index === step ? "current" : index < step ? "done" : "")}>
                  <span className="rail-icon">{index < step ? <Check size={15} /> : index + 1}</span><span><strong>{item[0]}</strong><small>{item[1]}</small></span>
                </button>)}
              </nav>
              <div className="form-card">
                <div className="card-step-label">ETAPA {step + 1} DE 7</div>
                <h2>{steps[step][0]}</h2>
                <p className="form-intro">{step === 0 ? "Identifique o aluno para quem o coordenador está preparando o parecer." :
                  step === 1 ? "Informe a instituição e o curso em que o aluno cursou as disciplinas." :
                  step === 2 ? "Selecione o curso e a matriz curricular da universidade de destino." :
                  step === 3 ? "Anexe os documentos que serão usados na análise de aproveitamento." :
                  step === 4 ? "A extração organiza os dados do histórico; a IA poderá sugerir correspondências quando conectada." :
                  step === 5 ? "Confira as evidências e registre a decisão acadêmica para cada sugestão." :
                  "Gere o parecer com os itens revisados e aprovados pelo coordenador."}</p>
                {step === 0 && <div className="student-picker">
                  {form.student_id ? <div className="selected-student"><div className="table-avatar">{(form.student_name || "A").split(" ").map((s) => s[0]).slice(0,2).join("")}</div><div><strong>{form.student_name}</strong><small>{form.student_ra ? "RA " + form.student_ra : "RA não informado"} · cadastro reutilizável</small></div><button className="button button-quiet" onClick={() => { change("student_id", ""); setStudentSearch(""); }}>Trocar aluno</button></div> : <>
                    <label className="field">Localizar aluno cadastrado<div className="search-box student-search"><Search size={16} /><input value={studentSearch} onChange={(e) => setStudentSearch(e.target.value)} placeholder="Buscar por nome ou RA" /></div></label>
                    <div className="student-results">{students.slice(0, 5).map((student) => <div className="student-option-row" key={student.id}><button className="student-option" onClick={() => { setForm((current) => ({ ...current, student_id: String(student.id), student_name: student.name, student_ra: student.ra || "" })); setEditingStudent(null); setNotice(""); }}><span className="table-avatar">{student.name.split(" ").map((s) => s[0]).slice(0,2).join("")}</span><span><strong>{student.name}</strong><small>{student.ra ? "RA " + student.ra : "RA não informado"}</small></span><ArrowRight size={15} /></button><button className="edit-student-button" onClick={() => { setEditingStudent({ id: student.id, name: student.name, ra: student.ra || "" }); setShowRegisterStudent(false); }}>Editar</button></div>)}</div>
                    {editingStudent && <div className="register-form field-grid"><label className="field full">Nome completo<input value={editingStudent.name} onChange={(e) => setEditingStudent({ ...editingStudent, name: e.target.value })} /></label><label className="field full">RA · opcional<input value={editingStudent.ra} onChange={(e) => setEditingStudent({ ...editingStudent, ra: e.target.value })} /></label><div className="student-edit-actions"><button className="button button-quiet" onClick={() => setEditingStudent(null)}>Cancelar</button><button className="button button-primary" onClick={saveStudentEdit} disabled={registerBusy}>{registerBusy ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Salvar alterações</button></div></div>}
                    <div className="register-divider"><span>ou</span></div>
                    <button className="button button-secondary" onClick={() => setShowRegisterStudent((v) => !v)}><Plus size={15} /> Cadastrar novo aluno</button>
                    {showRegisterStudent && <div className="register-form field-grid"><label className="field full">Nome completo<input value={form.student_name} onChange={(e) => change("student_name", e.target.value)} placeholder="Nome do aluno" /></label><label className="field full">RA · opcional<input value={form.student_ra} onChange={(e) => change("student_ra", e.target.value)} placeholder="RA, se disponível" /></label><button className="button button-primary" onClick={registerStudent} disabled={registerBusy}>{registerBusy ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Salvar cadastro</button></div>}
                  </>}
                  <div className="inline-note student-note"><UserRound size={16} /><span>O cadastro do aluno é independente. Um mesmo aluno pode ter várias análises; seus dados não serão duplicados.</span></div>
                </div>}
                {step === 1 && <div className="field-grid"><label className="field">Instituição de origem<input value={form.origin_institution} onChange={(e) => change("origin_institution", e.target.value)} placeholder="Nome da instituição" /></label><label className="field">Curso de origem<input value={form.origin_course} onChange={(e) => change("origin_course", e.target.value)} placeholder="Ex.: Administração" /></label><label className="field">Situação do curso<select value={form.origin_status} onChange={(e) => change("origin_status", e.target.value)}><option value="">Selecione</option><option>Concluído</option><option>Incompleto</option><option>Trancado</option></select></label></div>}
                {step === 2 && <div className="field-grid"><label className="field">Curso de destino<select value={form.target_course_id} onChange={(e) => { change("target_course_id", e.target.value); change("target_matrix_id", ""); }}><option value="">Selecione o curso</option>{courses.map((c) => <option key={c.id} value={c.id}>{c.name} · {c.code}</option>)}</select></label><label className="field">Matriz curricular<select value={form.target_matrix_id} onChange={(e) => change("target_matrix_id", e.target.value)} disabled={!matrices.length}><option value="">Selecione a matriz</option>{matrices.map((m) => <option key={m.id} value={m.id}>{m.code}</option>)}</select></label><label className="field">Período de ingresso<input value={form.term} onChange={(e) => change("term", e.target.value)} placeholder="Ex.: 1/2027" /></label><div className="inline-note full"><GraduationCap size={17} /><span>A matriz define as disciplinas de destino usadas na comparação. Informe o período em que o aluno ingressará na universidade.</span></div></div>}
                {step === 3 && <div className="upload-stack"><FileDrop title="Histórico acadêmico" hint="Obrigatório · PDF ou DOCX · até 20 MB" file={form.history} onFile={(file) => change("history", file)} onRemove={() => change("history", null)} /><FileDrop title="Planos de ensino da origem" hint="Opcional · envie um ou mais PDFs/DOCX" multiple files={form.plans} onFiles={(files) => change("plans", files)} onRemove={(index) => change("plans", form.plans.filter((_, i) => i !== index))} /></div>}
                {step === 4 && <AnalysisPanel analysis={analysis} busy={busy} onExtract={runExtraction} onAnalyze={runAi} onReview={async (rows) => { try { const value = await saveHistoryReview(activeId, rows, true); setAnalysis(value); setNotice("Dados do histórico confirmados pelo coordenador."); } catch (e) { setError(e.message); } }} />}
                {step === 5 && <ReviewPanel analysis={analysis} onDecision={saveDecision} onManual={async (data) => { try { setAnalysis(await addManualSuggestion(activeId, data)); setNotice("Correspondência manual adicionada à fila de revisão."); } catch (e) { setError(e.message); } }} />}
                {step === 6 && <ReportPreview analysis={analysis} note={coordinatorNote} setNote={setCoordinatorNote} busy={busy} onDownload={makeReport} />}
                <div className="form-footer"><button className="button button-quiet" onClick={() => step === 0 ? setScreen("home") : setStep(step - 1)}><ArrowLeft size={16} /> Voltar</button>
                  {step < 4 && <button className="button button-primary" onClick={continueStep} disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : null}{step === 3 ? "Registrar e continuar" : "Continuar"}<ArrowRight size={16} /></button>}
                  {step === 4 && analysis?.ai_analysis_done && <button className="button button-primary" onClick={() => setStep(5)}>Ir para revisão <ArrowRight size={16} /></button>}
                  {step === 5 && <button className="button button-primary" onClick={() => setStep(6)}>Concluir revisão <ArrowRight size={16} /></button>}
                </div>
              </div>
            </div>
          </section>
        ) : screen === "home" ? (
          <Dashboard analyses={analyses} onNew={openNew} onOpen={openAnalysis} onList={() => setScreen("list")} />
        ) : screen === "students" ? (
          <Students students={students} search={studentSearch} setSearch={setStudentSearch} onSave={async (student) => {
            try {
              const updated = await updateStudent(student.id, { name: student.name, ra: student.ra });
              setStudents((current) => current.map((item) => item.id === updated.id ? updated : item));
              setNotice("Cadastro do aluno atualizado."); setError("");
            } catch (e) { setError(e.message); }
          }} />
        ) : (
          <section className="content">
            <div className="page-heading"><div><div className="eyebrow">ACOMPANHAMENTO</div><h1>Análises</h1><p>Solicitações de aproveitamento acompanhadas pela coordenação.</p></div><button className="button button-primary" onClick={openNew}><Plus size={16} /> Nova análise</button></div>
            <AnalysisList analyses={filtered} search={search} setSearch={setSearch} onOpen={openAnalysis} />
          </section>
        )}
      </main>
    </div>
  );
}

function FileDrop({ title, hint, file, files = [], multiple, onFile, onFiles, onRemove }) {
  const inputRef = useRef(null);
  const picked = multiple ? files : file ? [file] : [];
  function handleFileChange(event) {
    const selected = Array.from(event.target.files || []);
    if (multiple) onFiles(selected);
    else onFile(selected[0] || null);
    event.target.value = "";
  }
  return <div className="file-drop"><input ref={inputRef} type="file" accept=".pdf,.docx" multiple={multiple} onChange={handleFileChange} /><div className="upload-icon"><Upload size={19} /></div><div className="file-copy"><strong>{title}</strong><span>{hint}</span>{picked.map((f, i) => <small className="file-chip" key={f.name}><FileText size={13} />{f.name}{onRemove && <button type="button" className="remove-file" onClick={() => onRemove(i)} aria-label={"Remover " + f.name}><X size={13} /></button>}</small>)}</div><span className="button button-quiet browse-button">Escolher arquivo</span></div>;
}
function Dashboard({ analyses, onNew, onOpen, onList }) {
  const waiting = analyses.filter((a) => a.status === "review").length;
  const recent = analyses.slice(0, 5);
  return <section className="content">
    <div className="welcome-row"><div><div className="eyebrow">ÁREA DA COORDENAÇÃO</div><h1>Painel da coordenação</h1><p>Acompanhe as análises de aproveitamento abertas para os alunos.</p></div><button className="button button-primary" onClick={onNew}><Plus size={16} /> Nova análise</button></div>
    <div className="metric-grid"><Metric icon={<Activity size={18} />} label="Análises em andamento" value={analyses.length} trend="Solicitações cadastradas" tone="blue" /><Metric icon={<Clock3 size={18} />} label="Aguardando revisão" value={waiting} trend="Precisam de decisão" tone="amber" /><Metric icon={<CheckCircle2 size={18} />} label="Concluídas" value={analyses.filter((a) => a.status === "complete").length} trend="Pareceres emitidos" tone="green" /></div>
    <div className="dashboard-grid"><section className="panel recent-panel"><div className="panel-heading"><div><h2>Solicitações recentes</h2><p>Últimas análises abertas pela coordenação</p></div><button className="text-button" onClick={onList}>Ver todas <ArrowRight size={14} /></button></div>{recent.length ? <AnalysisList analyses={recent} compact onOpen={onOpen} /> : <div className="empty-state"><div className="empty-art"><FileText size={26} /></div><strong>Nenhuma análise cadastrada</strong><span>Inicie um processo de aproveitamento para um aluno.</span><button className="button button-secondary" onClick={onNew}><Plus size={15} /> Nova análise</button></div>}</section><aside className="panel guide-panel"><div className="guide-eyebrow"><Sparkles size={15} /> FLUXO DO COORDENADOR</div><h2>Da documentação ao parecer</h2><p>Organize os documentos, acompanhe a análise e registre sua decisão em um só lugar.</p><div className="guide-steps">{["Identifique o aluno e os cursos", "Anexe histórico e planos de ensino", "Revise as sugestões e evidências", "Emita o parecer acadêmico"].map((s, i) => <div key={s}><span>{i + 1}</span>{s}</div>)}</div><button className="guide-link" onClick={onNew}>Começar uma análise <ArrowRight size={14} /></button></aside></div>
  </section>;
}
function Metric({ icon, label, value, trend, tone }) { return <div className="metric-card"><span className={"metric-icon " + tone}>{icon}</span><span className="metric-label">{label}</span><strong>{value}</strong><small>{trend}</small></div>; }
function Students({ students, search, setSearch, onSave }) {
  const [editing, setEditing] = useState(null);
  const matches = students.filter((student) => (student.name + " " + (student.ra || "")).toLowerCase().includes(search.toLowerCase()));
  return <section className="content"><div className="page-heading"><div><div className="eyebrow">CADASTROS REUTILIZÁVEIS</div><h1>Alunos</h1><p>Consulte e atualize cadastros usados em várias análises.</p></div></div>
    <div className="panel"><div className="table-tools"><label className="search-box"><Search size={16} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar por nome ou RA" /></label><span className="muted small">{matches.length} encontrados</span></div>
      {matches.length ? <table><thead><tr><th>NOME</th><th>RA</th><th></th></tr></thead><tbody>{matches.map((student) => <tr key={student.id}><td>{editing?.id === student.id ? <input className="student-edit-input" value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} /> : <strong>{student.name}</strong>}</td><td>{editing?.id === student.id ? <input className="student-edit-input" value={editing.ra} onChange={(e) => setEditing({ ...editing, ra: e.target.value })} placeholder="Opcional" /> : student.ra || "Não informado"}</td><td>{editing?.id === student.id ? <><button className="button button-quiet" onClick={() => setEditing(null)}>Cancelar</button> <button className="button button-primary" onClick={() => { onSave(editing); setEditing(null); }}>Salvar</button></> : <button className="button button-quiet" onClick={() => setEditing({ id: student.id, name: student.name, ra: student.ra || "" })}>Editar</button>}</td></tr>)}</tbody></table> : <div className="table-empty">Nenhum aluno encontrado. Os cadastros podem ser criados ao iniciar uma análise.</div>}
    </div></section>;
}
function AnalysisList({ analyses, search, setSearch, onOpen, compact }) {
  return <div className="table-wrap">{!compact && <div className="table-tools"><label className="search-box"><Search size={16} /><input value={search || ""} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar por aluno, curso ou protocolo" /></label><button className="button button-quiet"><Menu size={15} /> Filtros</button></div>}
    {analyses.length ? <table><thead><tr><th>ALUNO / PROTOCOLO</th><th>CURSO DE ORIGEM</th><th>CURSO DE DESTINO</th><th>ETAPA</th><th>ATUALIZADO</th><th></th></tr></thead><tbody>{analyses.map((a) => <tr key={a.id} onClick={() => onOpen(a.id)}><td><div className="student-cell"><div className="table-avatar">{(a.student_name || "A").split(" ").map((s) => s[0]).slice(0, 2).join("")}</div><div><strong>{a.student_name || "Aluno"}</strong><small>EQ-{String(a.id).padStart(5, "0")}</small></div></div></td><td>{a.origin_course || "—"}</td><td>{a.target_course || "—"}</td><td><span className={"status-pill " + (a.status === "complete" ? "status-done" : a.status === "review" ? "status-review" : "status-progress")}><i />{a.stage || (a.status === "complete" ? "Concluída" : "Em andamento")}</span></td><td>{a.updated_at || "Agora"}</td><td><button className="row-arrow"><ArrowRight size={16} /></button></td></tr>)}</tbody></table> : <div className="table-empty">Nenhum resultado encontrado.</div>}</div>;
}
function AnalysisPanel({ analysis, busy, onExtract, onAnalyze, onReview }) {
  const [edited, setEdited] = useState([]);
  useEffect(() => { setEdited((analysis?.extraction?.rows || []).map((r) => ({ ...r }))); }, [analysis]);
  if (!analysis) return <div className="empty-stage"><FileText size={22} /><strong>Solicitação ainda não carregada</strong><span>Volte e conclua o cadastro do aluno e dos documentos.</span></div>;
  const rows = analysis.extraction?.rows || [];
  return <div className="analysis-stage">
    <div className="stage-summary"><span className="summary-icon"><FileText size={18} /></span><div><strong>Histórico acadêmico</strong><small>{analysis.history_name || "Documento anexado"}</small></div><span className="tag tag-ready"><CheckCircle2 size={13} /> Recebido</span></div>
    {!analysis.extraction ? <div className="ai-prep"><div className="ai-orb"><Sparkles size={21} /></div><h3>Pronto para analisar o histórico</h3><p>O sistema primeiro lê os dados estruturados. Quando o agente de equivalências estiver conectado, ele receberá essas disciplinas, os planos de ensino e a matriz de destino.</p><button className="button button-primary" onClick={onExtract} disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <Sparkles size={16} />} Ler histórico</button><div className="ai-contract"><span className="contract-dot" /> Integração preparada · agente de IA ainda não configurado</div></div> : <>
      {analysis.extraction.warning && <div className="inline-warning">{analysis.extraction.warning}</div>}
      <div className="table-heading"><div><strong>Disciplinas identificadas</strong><span>{rows.length} itens · revise antes de confirmar</span></div><span className="tag tag-neutral">Leitura de documento</span></div>
      <div className="editable-table-wrap"><table className="editable-table"><thead><tr><th>DISCIPLINA</th><th>CÓDIGO</th><th>CARGA</th><th>SITUAÇÃO</th></tr></thead><tbody>{edited.map((r, i) => <tr key={r.id || i}><td><input value={r.name || ""} onChange={(e) => setEdited(edited.map((x, ix) => ix === i ? { ...x, name: e.target.value } : x))} /></td><td><input value={r.code || ""} onChange={(e) => setEdited(edited.map((x, ix) => ix === i ? { ...x, code: e.target.value } : x))} /></td><td><input value={r.hours || ""} onChange={(e) => setEdited(edited.map((x, ix) => ix === i ? { ...x, hours: e.target.value } : x))} /></td><td><input value={r.status || ""} onChange={(e) => setEdited(edited.map((x, ix) => ix === i ? { ...x, status: e.target.value } : x))} /></td></tr>)}</tbody></table></div>
      <button className="button button-secondary save-review" onClick={() => onReview(edited)} disabled={!rows.length || busy}>{busy ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Confirmar dados extraídos</button>
      <div className="ai-next"><div><Sparkles size={17} /><span><strong>Sugestões de equivalência por IA</strong><small>O agente poderá comparar ementas, conteúdos e carga horária.</small></span></div><button className="button button-primary" onClick={onAnalyze} disabled={!analysis.extraction.confirmed || busy} title={!analysis.extraction.confirmed ? "Confirme os dados extraídos para continuar" : ""}>Solicitar análise <ArrowRight size={15} /></button></div>
    </>}
  </div>;
}
function ReviewPanel({ analysis, onDecision, onManual }) {
  const suggestions = analysis?.suggestions || [];
  return <div className="review-stage">{!suggestions.length && <div className="empty-stage"><Sparkles size={22} /><strong>Nenhuma sugestão automática</strong><span>Sem IA conectada, o coordenador pode registrar a correspondência manualmente. As regras de aprovação e carga horária continuam valendo.</span></div>}{suggestions.map((s) => <article className="suggestion-card" key={s.id}><div className="suggestion-top"><div><span className="suggestion-label">{s.provider === "manual" ? "CORRESPONDÊNCIA MANUAL" : "SUGESTÃO DE EQUIVALÊNCIA"}</span><h3>{s.origin_name} <ArrowRight size={15} /> {s.target_name}</h3></div>{s.confidence != null && <span className="confidence">{Math.round(s.confidence * 100)}% confiança</span>}</div><p>{s.rationale}</p><div className="evidence-box"><strong><ShieldCheck size={14} /> Evidências consideradas</strong><span>{s.evidence_summary || (typeof s.evidence === "string" ? s.evidence : JSON.stringify(s.evidence || {})) || "Critérios registrados pelo coordenador"}</span></div><div className="suggestion-actions"><span className="tag tag-neutral">{s.decision === "pending" ? "Pendente de revisão" : s.decision === "approved" ? "Aprovada" : "Rejeitada"}</span><div><button className="button button-quiet" onClick={() => onDecision(s.id, "rejected")}>Recusar</button><button className="button button-primary" onClick={() => onDecision(s.id, "approved")}><Check size={15} /> Aprovar</button></div></div></article>)}<ManualSuggestionForm analysisId={analysis?.id} onSubmit={onManual} />
  </div>;
}

function ManualSuggestionForm({ analysisId, onSubmit }) {
  const [candidates, setCandidates] = useState([]);
  const [selection, setSelection] = useState("");
  const [rationale, setRationale] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => { if (analysisId) getCandidates(analysisId).then(setCandidates).catch((e) => setMessage(e.message)); }, [analysisId]);
  const pair = candidates.find((item) => item.source.id + ":" + item.target.id === selection);
  const save = async () => {
    if (!pair || !rationale.trim()) return setMessage("Escolha as disciplinas e descreva a justificativa.");
    setSaving(true); setMessage("");
    try { await onSubmit({ source_id: pair.source.id, target_id: pair.target.id, rationale: rationale.trim() }); setSelection(""); setRationale(""); }
    finally { setSaving(false); }
  };
  return <section className="manual-suggestion"><div><strong>Adicionar correspondência manual</strong><span>Somente disciplinas de origem aprovadas e com carga horária suficiente aparecem.</span></div><label className="field">Disciplina de origem e destino<select value={selection} onChange={(e) => setSelection(e.target.value)}><option value="">Selecione a correspondência</option>{candidates.map((item) => <option key={item.source.id + ":" + item.target.id} value={item.source.id + ":" + item.target.id}>{item.source.name} ({item.source.hours}h) → {item.target.name} ({item.target.hours}h)</option>)}</select></label><label className="field">Justificativa<input value={rationale} onChange={(e) => setRationale(e.target.value)} placeholder="Registre a justificativa da coordenação" /></label>{message && <small className="manual-message">{message}</small>}<button className="button button-secondary" onClick={save} disabled={saving || !candidates.length}>{saving ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />} Adicionar para revisão</button></section>;
}

function ReportPreview({ analysis, note, setNote, busy, onDownload }) {
  return <div className="report-preview">
    <div className="result-panel report-ready"><div className="result-icon"><FileCheck2 size={27} /></div><h3>Prévia do parecer</h3><p>Confira os dados que serão incluídos antes de baixar o documento.</p></div>
    <div className="preview-sheet"><div className="preview-brand">UNIPAR <span>· Coordenação acadêmica</span></div><h3>Parecer de aproveitamento de estudos</h3><div className="preview-meta"><div><small>ALUNO</small><strong>{analysis?.student_name || "—"}</strong></div><div><small>RA</small><strong>{analysis?.student_ra || "Não informado"}</strong></div><div><small>INSTITUIÇÃO DE ORIGEM</small><strong>{analysis?.origin_institution || "—"}</strong></div><div><small>CURSO DE DESTINO</small><strong>{analysis?.target_course || "—"} · Matriz {analysis?.target_matrix || "—"}</strong></div></div><div className="preview-table-title">Resultado das equivalências · {analysis?.suggestions?.length || 0}</div><table className="preview-table"><thead><tr><th>DISCIPLINA DE ORIGEM</th><th>DISCIPLINA DE DESTINO</th><th>DECISÃO</th></tr></thead><tbody>{(analysis?.suggestions || []).map((item) => <tr key={item.id}><td>{item.origin_name}</td><td>{item.target_name}</td><td>{item.decision === "approved" ? "Aprovada" : item.decision === "rejected" ? "Não aprovada" : "Pendente"}</td></tr>)}{!analysis?.suggestions?.length && <tr><td colSpan="3">Nenhuma equivalência sugerida ou registrada até o momento.</td></tr>}</tbody></table></div>
    <label className="field coordinator-note">Observação da coordenação<input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Opcional · será incluída no parecer" /></label>
    <div className="report-actions"><span className="muted small">O parecer incluirá itens aprovados, não aprovados e pendentes para conferência da coordenação.</span><button className="button button-primary" onClick={onDownload} disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <ArrowDownToLine size={16} />} Baixar parecer</button></div>
  </div>;
}

export default App;
