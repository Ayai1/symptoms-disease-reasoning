import { useState } from "react";

export default function App() {

  const [input, setInput] = useState("");
  const [result, setResult] = useState(null);
  const [answers, setAnswers] = useState({});
  const [finalResult, setFinalResult] = useState(null);
  const [chat, setChat] = useState([]);

  // =============================
  // INITIAL DIAGNOSIS
  // =============================
  const runDiagnosis = async () => {

    const userSymptoms = input.split(",").map(s => s.trim());

    setChat(prev => [
      ...prev,
      { role:"user", text: input }
    ]);

    try {

      const res = await fetch("http://127.0.0.1:8000/diagnose", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          symptoms: userSymptoms
        })
      });

      const data = await res.json();

      setResult(data);
      setFinalResult(null);
      setAnswers({});

      setChat(prev => [
        ...prev,
        {
          role:"ai",
          text:`Top hypothesis: ${data.diagnoses[0].disease}`
        },
        {
          role:"ai",
          text:data.tree[0].next_questions[0].question
        }
      ]);

    } catch(e) {
      console.error(e);
    }
  };

  // =============================
  // REALTIME ToT UPDATE
  // =============================
  const answerQuestion = async (symptom, value) => {

    const newAnswers = {
      ...answers,
      [symptom]: value
    };

    setAnswers(newAnswers);

    setChat(prev => [
      ...prev,
      { role:"user", text:value }
    ]);

    try {

      const res = await fetch("http://127.0.0.1:8000/update_tree", {
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body:JSON.stringify({
          tree: result.tree,
          answers: newAnswers
        })
      });

      const data = await res.json();

      setResult(prev => ({
        ...prev,
        tree:data.tree
      }));

      if(data.final){

        setFinalResult(data.final);

        setChat(prev => [
          ...prev,
          {
            role:"ai",
            text:`Final Diagnosis: ${data.final.disease}`
          }
        ]);

        return;
      }

      // ⭐ ask NEXT question only
      const nextQ = data.tree[0].next_questions?.[0];

      if(nextQ){
        setChat(prev => [
          ...prev,
          { role:"ai", text: nextQ.question }
        ]);
      }

    } catch(e){
      console.error(e);
    }
  };

  // =============================
  // UI
  // =============================
  return (
  <div style={{
    padding:40,
    fontFamily:"Segoe UI, Arial",
    maxWidth:700,
    margin:"auto",
    background:"#0f172a",
    minHeight:"100vh",
    color:"#e5e7eb"
  }}>

    <h2 style={{marginBottom:20}}>🧠 AI Medical Assistant</h2>

    {/* CHAT WINDOW */}
    <div style={{
      borderRadius:12,
      padding:20,
      height:420,
      overflowY:"auto",
      background:"#020617",
      border:"1px solid #1f2937",
      marginBottom:20
    }}>

      {chat.map((msg,i)=>(
        <div key={i} style={{
          textAlign: msg.role==="user" ? "right":"left",
          marginBottom:14
        }}>
          <span style={{
            display:"inline-block",
            padding:"10px 14px",
            borderRadius:14,
            maxWidth:"80%",
            lineHeight:1.5,
            fontSize:15,
            background: msg.role==="user"
              ? "#2563eb"
              : "#111827",
            color:"#f9fafb"
          }}>
            {msg.text}
          </span>
        </div>
      ))}

    </div>

    {/* INPUT */}
    {!result && (
      <>
        <input
          style={{
            padding:12,
            width:420,
            borderRadius:8,
            border:"1px solid #374151",
            background:"#020617",
            color:"#f9fafb"
          }}
          placeholder="fever, cough, breathing difficulty"
          value={input}
          onChange={(e)=>setInput(e.target.value)}
        />

        <button
          onClick={runDiagnosis}
          style={{
            marginLeft:10,
            padding:"12px 18px",
            borderRadius:8,
            background:"#2563eb",
            color:"white",
            border:"none",
            cursor:"pointer"
          }}
        >
          Send
        </button>
      </>
    )}

    {/* YES / NO */}
    {result && !finalResult && result.tree?.[0]?.next_questions?.[0] && (
      <div style={{marginTop:10}}>

        <button
          style={{
            padding:"10px 18px",
            borderRadius:8,
            background:"#16a34a",
            color:"white",
            border:"none",
            cursor:"pointer"
          }}
          onClick={()=>answerQuestion(
            result.tree[0].next_questions[0].symptom,
            "yes"
          )}
        >
          Yes
        </button>

        <button
          style={{
            marginLeft:10,
            padding:"10px 18px",
            borderRadius:8,
            background:"#dc2626",
            color:"white",
            border:"none",
            cursor:"pointer"
          }}
          onClick={()=>answerQuestion(
            result.tree[0].next_questions[0].symptom,
            "no"
          )}
        >
          No
        </button>

      </div>
    )}

    {/* LITERATURE */}
    {finalResult && result?.diagnoses?.[0]?.literature_support && (
      <div style={{marginTop:25}}>
        <h4 style={{color:"#93c5fd"}}>📚 Literature Support</h4>
        <ul>
          {result.diagnoses[0].literature_support.map((e,i)=>(
            <li key={i} style={{marginBottom:6}}>
              {e.title}
            </li>
          ))}
        </ul>
      </div>
    )}

  </div>
)};