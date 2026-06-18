// Interview.jsx — Stage 3
// Paper: "System generates 8-12 role-specific interview questions.
//         Candidates respond under timed conditions.
//         Timed response constraints simulate actual interview conditions."

import { useState, useEffect, useRef } from "react";
import { useApp } from "../context/AppContext";
import { generateQuestions, evaluateAllAnswers } from "../api/axiosClient";
import "./pages.css";

const TIME_LIMIT = 120; // 2 minutes per question — paper: timed constraints

export default function Interview() {
  const {
    resumeData, selectedRole, skillGapData,
    setQuestions, setAnswers, setInterviewData, setCurrentStage,
  } = useApp();

  const [questions,   setLocalQuestions] = useState([]);
  const [currentIdx,  setCurrentIdx]     = useState(0);
  const [answers,     setLocalAnswers]   = useState([]);
  const [currentAns,  setCurrentAns]     = useState("");
  const [timeLeft,    setTimeLeft]       = useState(TIME_LIMIT);
  const [loading,     setLoading]        = useState(true);
  const [submitting,  setSubmitting]     = useState(false);
  const [error,       setError]          = useState("");
  const timerRef = useRef(null);

  // Generate questions on mount
  useEffect(() => {
    (async () => {
      try {
        const res = await generateQuestions({
          job_role:         selectedRole,
          resume_text:      resumeData?.parsed_text || "",
          skill_gaps:       skillGapData?.missing_skills || [],
          matched_skills:   skillGapData?.matched_skills || [],
          experience_level: resumeData?.experience?.level,
          questions_per_type: 3, // 4 types × 3 = 12 questions
        });
        if (res.data.success) {
          setLocalQuestions(res.data.questions);
          setQuestions(res.data.questions);
          startTimer();
        } else {
          setError("Failed to generate questions.");
        }
      } catch (e) {
        setError("Server error generating questions.");
      } finally {
        setLoading(false);
      }
    })();
    return () => clearInterval(timerRef.current);
  }, []);

  // Timer — paper: "timed response constraints"
  const startTimer = () => {
    clearInterval(timerRef.current);
    setTimeLeft(TIME_LIMIT);
    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) { clearInterval(timerRef.current); handleNext(true); return 0; }
        return t - 1;
      });
    }, 1000);
  };

  const handleNext = (timedOut = false) => {
    clearInterval(timerRef.current);
    const ans = timedOut && !currentAns ? "[No answer — timed out]" : currentAns;
    const updated = [...answers, {
      question:         questions[currentIdx]?.question || "",
      candidate_answer: ans,
      question_type:    questions[currentIdx]?.type || "technical",
      skill:            questions[currentIdx]?.skill || "",
      job_role:         selectedRole,
    }];
    setLocalAnswers(updated);
    setCurrentAns("");

    if (currentIdx + 1 < questions.length) {
      setCurrentIdx(currentIdx + 1);
      startTimer();
    } else {
      handleSubmitAll(updated);
    }
  };

  const handleSubmitAll = async (allAnswers) => {
    setSubmitting(true);
    try {
      const res = await evaluateAllAnswers({ answers: allAnswers });
      if (res.data) {
        setAnswers(allAnswers);
        setInterviewData(res.data);
        setCurrentStage(4);
      }
    } catch (e) {
      setError("Evaluation failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const timerColor = timeLeft > 60 ? "#10b981" : timeLeft > 30 ? "#f59e0b" : "#ef4444";
  const progress   = (currentIdx / (questions.length || 1)) * 100;

  if (loading)    return <div className="stage-container"><div className="loading">Generating your personalized interview questions...</div></div>;
  if (submitting) return <div className="stage-container"><div className="loading">Evaluating your answers...</div></div>;
  if (error)      return <div className="stage-container"><div className="error-msg">⚠️ {error}</div></div>;

  const q = questions[currentIdx];

  return (
    <div className="stage-container">
      <div className="stage-header">
        <span className="stage-badge">Stage 3 of 5</span>
        <h1>AI Interview Simulation</h1>
        <p>Answer each question within the time limit. Be specific and structured.</p>
      </div>

      {/* Progress bar */}
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <div className="progress-label">
        Question {currentIdx + 1} of {questions.length}
      </div>

      <div className="card">
        {/* Timer — paper: timed conditions */}
        <div className="timer" style={{ color: timerColor }}>
          ⏱ {Math.floor(timeLeft / 60)}:{String(timeLeft % 60).padStart(2, "0")}
          <span className="timer-label">remaining</span>
        </div>

        {/* Question type badge */}
        <div className="question-meta">
          <span className={`type-badge type-${q?.type}`}>
            {q?.type?.replace("_", " ")}
          </span>
          {q?.skill && <span className="skill-badge">{q.skill}</span>}
          {q?.difficulty && <span className="diff-badge">{q.difficulty}</span>}
        </div>

        {/* Question */}
        <div className="question-text">{q?.question}</div>

        {/* Answer input */}
        <textarea
          className="textarea answer-input"
          rows={6}
          placeholder="Type your answer here... Be specific with examples."
          value={currentAns}
          onChange={(e) => setCurrentAns(e.target.value)}
        />
        <small>{currentAns.split(" ").filter(Boolean).length} words</small>

        <button
          className="btn-primary"
          onClick={() => handleNext(false)}
          disabled={!currentAns.trim()}
        >
          {currentIdx + 1 === questions.length ? "Submit Interview →" : "Next Question →"}
        </button>
      </div>
    </div>
  );
}