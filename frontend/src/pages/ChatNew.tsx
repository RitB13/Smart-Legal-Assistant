import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import Layout from "../components/Layout";

interface Message {
  id: string;
  text: string;
  sender: "user" | "bot";
  timestamp: Date;
  language?: string;
  messageType?: "text" | "prediction_result";
}

interface CaseContext {
  case_name?: string;
  case_type?: string;
  jurisdiction_state?: string;
  year?: number;
  damages_awarded?: number;
  parties_count?: number;
  is_appeal?: boolean;
  case_summary?: string;
  confidence?: number;
  missing_fields?: string[];
}

interface PredictionQuestion {
  question_id: string;
  question_text: string;
  field_name: string;
  question_type: string;
  options?: string[];
  placeholder?: string;
  hints?: string;
}

const ChatPage = () => {
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, []);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      text: "👋 Welcome to Smart Legal Assistant!\n\nI can help you in two ways:\n\n**1️⃣ Chat & Get Guidance** - Ask me legal questions and I'll explain your rights and provide advice.\n\n**2️⃣ Predict Case Outcome** - Tell me about your case and I'll predict the likely outcome with detailed analysis.\n\nJust describe your legal situation and I'll intelligently guide you!",
      sender: "bot",
      timestamp: new Date(),
      language: "en",
    }
  ]);

  const [inputText, setInputText] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [mode, setMode] = useState<"chat" | "predict" | null>(null);
  const [caseContext, setCaseContext] = useState<CaseContext | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<PredictionQuestion | null>(null);
  const [askedQuestions, setAskedQuestions] = useState<string[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isFirstLoad = useRef(true);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isFirstLoad.current) {
      isFirstLoad.current = false;
      return;
    }
    scrollToBottom();
  }, [messages]);

  // Step 1: Decide mode (chat vs predict)
  const decideMode = async (userText: string) => {
    try {
      const response = await fetch(`${apiUrl}/chat-intelligence/decide-mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_message: userText,
          conversation_history: messages.map(m => ({
            text: m.text,
            sender: m.sender,
            timestamp: m.timestamp.toISOString(),
          })),
          language: "en",
        }),
      });

      if (!response.ok) throw new Error("Failed to decide mode");
      const decision = await response.json();

      return {
        suggestedMode: decision.suggested_mode,
        followUp: decision.follow_up_message,
      };
    } catch (error) {
      console.error("Mode decision error:", error);
      return { suggestedMode: "chat", followUp: "Let me help you with your legal question." };
    }
  };

  // Step 2: Extract context from chat
  const extractContext = async () => {
    const userMessages =  messages.filter(m => m.sender === "user");
    if (userMessages.length === 0) return null;

    try {
      const response = await fetch(`${apiUrl}/chat-intelligence/extract-context`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: userMessages.map(m => ({
            text: m.text,
            sender: m.sender,
            timestamp: m.timestamp.toISOString(),
          })),
          language: "en",
        }),
      });

      if (!response.ok) throw new Error("Failed to extract context");
      const context = await response.json();
      return context;
    } catch (error) {
      console.error("Context extraction error:", error);
      return null;
    }
  };

  // Step 3: Get next prediction question
  const getNextQuestion = async (context: CaseContext) => {
    try {
      const response = await fetch(`${apiUrl}/chat-intelligence/next-prediction-question`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          extracted_context: context,
          asked_questions: askedQuestions,
          language: "en",
        }),
      });

      if (!response.ok) throw new Error("Failed to get question");
      const question = await response.json();
      return question;
    } catch (error) {
      console.error("Question fetching error:", error);
      return null;
    }
  };

  // Step 4: Call case outcome prediction
  const predictCaseOutcome = async (context: CaseContext) => {
    try {
      const response = await fetch(`${apiUrl}/case-outcome/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_name: context.case_name || "Case",
          case_type: context.case_type || "unknown",
          year: context.year || new Date().getFullYear(),
          jurisdiction_state: context.jurisdiction_state || "unknown",
          damages_awarded: context.damages_awarded || 0,
          parties_count: context.parties_count || 2,
          is_appeal: context.is_appeal || false,
        }),
      });

      if (!response.ok) throw new Error("Prediction failed");
      const result = await response.json();
      return result;
    } catch (error) {
      console.error("Prediction error:", error);
      return null;
    }
  };

  // Step 5: Main handler for user message
  const handleSend = async () => {
    if (!inputText.trim()) return;

    const userText = inputText;
    const userMessage: Message = {
      id: Date.now().toString(),
      text: userText,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText("");
    setIsTyping(true);

    try {
      // If no mode decided yet, decide it now
      if (!mode) {
        const modeDecision = await decideMode(userText);
        setMode(modeDecision.suggestedMode as any);

        const followupBot: Message = {
          id: (Date.now() + 1).toString(),
          text: modeDecision.followUp,
          sender: "bot",
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, followupBot]);

        // If prediction mode, extract context and start questions
        if (modeDecision.suggestedMode === "predict") {
          const context = await extractContext();
          if (context) {
            setCaseContext(context);
            const nextQ = await getNextQuestion(context);
            if (nextQ && nextQ.question_id !== "q_done") {
              setCurrentQuestion(nextQ);

              const questionBot: Message = {
                id: (Date.now() + 2).toString(),
                text: `📋 **${nextQ.question_text}**${nextQ.hints ? `\n\n💡 Hint: ${nextQ.hints}` : ""}`,
                sender: "bot",
                timestamp: new Date(),
              };
              setMessages(prev => [...prev, questionBot]);
            }
          }
        } else {
          // Chat mode - call regular query endpoint
          const response = await fetch(`${apiUrl}/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: userText }),
          });

          if (response.ok) {
            const data = await response.json();
            const botResponse: Message = {
              id: (Date.now() + 1).toString(),
              text: data.summary || "I'll help you with this legal matter.",
              sender: "bot",
              timestamp: new Date(),
            };
            setMessages(prev => [...prev, botResponse]);
          }
        }
      } else if (mode === "predict" && currentQuestion) {
        // User answering a prediction question
        setAskedQuestions(prev => [...prev, currentQuestion.question_id]);

        // Update context with answer
        const updatedContext = {
          ...caseContext,
          [currentQuestion.field_name]: userText,
        };
        setCaseContext(updatedContext);

        // Get next question or predict
        const nextQ = await getNextQuestion(updatedContext);

        if (nextQ && nextQ.question_id === "q_done") {
          // All questions asked, time to predict!
          setCurrentQuestion(null);

          const processingBot: Message = {
            id: (Date.now() + 1).toString(),
            text: "🔍 Analyzing your case details and predicting the outcome...",
            sender: "bot",
            timestamp: new Date(),
          };
          setMessages(prev => [...prev, processingBot]);

          const prediction = await predictCaseOutcome(updatedContext);
          if (prediction) {
            const resultBot: Message = {
              id: (Date.now() + 2).toString(),
              text: `✅ **CASE OUTCOME PREDICTION**\n\n**Predicted Verdict:** ${prediction.verdict}\n**Confidence:** ${(prediction.probability * 100).toFixed(1)}%\n\n**Analysis:**\n${prediction.risk_assessment?.overall_risk ? `Risk Level: ${prediction.risk_assessment.overall_risk}` : ""}`,
              sender: "bot",
              timestamp: new Date(),
              messageType: "prediction_result",
            };
            setMessages(prev => [...prev, resultBot]);
            setCurrentQuestion(null);
          }
        } else if (nextQ) {
          setCurrentQuestion(nextQ);
          const questionBot: Message = {
            id: (Date.now() + 1).toString(),
            text: `📋 **${nextQ.question_text}**${nextQ.hints ? `\n\n💡 Hint: ${nextQ.hints}` : ""}`,
            sender: "bot",
            timestamp: new Date(),
          };
          setMessages(prev => [...prev, questionBot]);
        }
      } else if (mode === "chat") {
        // Continue chat mode
        const response = await fetch(`${apiUrl}/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: userText }),
        });

        if (response.ok) {
          const data = await response.json();
          const botResponse: Message = {
            id: (Date.now() + 1).toString(),
            text: data.summary || "I'll provide you with the information you need.",
            sender: "bot",
            timestamp: new Date(),
          };
          setMessages(prev => [...prev, botResponse]);
        }
      }
    } catch (error) {
      console.error("Error:", error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: "Sorry, I encountered an error processing your request. Please try again.",
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    }

    setIsTyping(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="text-center mb-8 animate-fade-up">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Smart Legal Assistant
          </h1>
          <p className="text-lg text-muted-foreground">
            Get legal guidance or predict case outcomes with AI-powered analysis
          </p>
        </div>

        <div className="border-2 border-black rounded-xl bg-card shadow-lg animate-fade-up overflow-hidden">
          {/* Chat Messages */}
          <div
            ref={chatContainerRef}
            className="h-[500px] overflow-y-auto p-6 space-y-4 scrollbar-thin"
          >
            {messages.map((message, index) => (
              <div
                key={message.id}
                className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"} animate-fade-up`}
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <div className={`flex max-w-[80%] ${message.sender === "user" ? "flex-row-reverse" : "flex-row"} items-start space-x-2`}>
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${message.sender === "user" ? "gradient-primary ml-2" : "bg-secondary mr-2"}`}>
                    {message.sender === "user" ? (
                      <User className="h-4 w-4 text-primary-foreground" />
                    ) : (
                      <Bot className="h-4 w-4 text-secondary-foreground" />
                    )}
                  </div>

                  <div className={`rounded-lg px-4 py-3 ${message.sender === "user" ? "gradient-primary text-primary-foreground" : message.messageType === "prediction_result" ? "bg-green-100 text-foreground border border-green-300" : "bg-muted text-foreground"}`}>
                    <p className="text-sm whitespace-pre-wrap">{message.text}</p>
                    <div className="flex items-center mt-2">
                      <p className={`text-xs ${message.sender === "user" ? "text-primary-foreground/70" : "text-muted-foreground"}`}>
                        {message.timestamp.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex justify-start animate-fade-up">
                <div className="flex items-start space-x-2">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                    <Bot className="h-4 w-4 text-secondary-foreground" />
                  </div>
                  <div className="bg-muted rounded-lg px-4 py-3">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{animationDelay: "0ms"}} />
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{animationDelay: "150ms"}} />
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{animationDelay: "300ms"}} />
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Section */}
          <div className="border-t border-border p-4">
            <div className="flex space-x-2">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={currentQuestion ? "Your answer..." : "Describe your legal situation..."}
                className="flex-1 px-4 py-2 rounded-lg border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-all"
              />
              <button
                onClick={handleSend}
                disabled={!inputText.trim() || isTyping}
                className="inline-flex items-center justify-center rounded-lg gradient-primary px-4 py-2 text-primary-foreground hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isTyping ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default ChatPage;
