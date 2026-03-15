import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, CheckCircle2, X, MessageCircle, TrendingUp, Zap, AlertTriangle } from "lucide-react";
import Layout from "../components/Layout";

// Enhanced message type system
type MessageType = "text" | "options" | "input" | "numeric_input" | "prediction_result" | "appeal_option";

interface Message {
  id: string;
  text: string;
  sender: "user" | "bot";
  timestamp: Date;
  type: MessageType;
  data?: {
    options?: string[];
    fieldName?: string;
    inputType?: string;
    prediction?: any;
  };
}

interface CaseContext {
  case_name?: string;
  case_type?: string;
  jurisdiction_state?: string;
  year?: number;
  damages_awarded?: number;
  is_appeal?: boolean;
  parties_count?: number;
}

// Prediction steps configuration - DATASET DRIVEN
// Case types and jurisdictions must match the preprocessing pipeline in LightGBM model
const PREDICTION_STEPS = [
  {
    step: 1,
    fieldName: "case_name",
    question: "What is the name or title of your case? (e.g., State vs John Doe)",
    type: "text_input",
    required: true,
  },
  {
    step: 2,
    fieldName: "case_type",
    question: "What type of case is this?",
    type: "options",
    // Options derived from preprocessing pipeline - case_outcome_predictor_service.py
    options: [
      "Criminal Complaint",
      "Property Dispute",
      "Dowry Harassment",
      "Harassment (Civil)",
      "Divorce (Contested)",
      "Divorce (Mutual Consent)",
      "Writ Petition",
      "Appeal",
    ],
    required: true,
  },
  {
    step: 3,
    fieldName: "jurisdiction_state",
    question: "Which state/jurisdiction is this case in? (e.g., Delhi, Mumbai, Bangalore)",
    type: "text_input",
    required: true,
    hint: "e.g., Delhi, Maharashtra, Karnataka, Tamil Nadu, Uttar Pradesh",
  },
  {
    step: 4,
    fieldName: "year",
    question: "What year was the case filed or decided?",
    type: "numeric_input",
    required: true,
    hint: "Year between 1950 and 2100",
  },
  {
    step: 5,
    fieldName: "damages_awarded",
    question: "Were damages awarded or claimed? (Enter amount in rupees, or 0 if none)",
    type: "numeric_input",
    required: false,
    hint: "Enter numeric value in rupees",
  },
  {
    step: 6,
    fieldName: "is_appeal",
    question: "Is this case an appeal or review of a previous verdict?",
    type: "appeal_option",
    required: false,
    options: ["Appeal or Review", "Original Case"],
    hint: "Select whether this is an appeal/review or an original case",
  },
];

// Reusable Components
const OptionButtons = ({
  options,
  onSelect,
  isLoading,
}: {
  options: string[];
  onSelect: (option: string) => void;
  isLoading?: boolean;
}) => (
  <div className="flex flex-wrap gap-2 mt-3">
    {options.map((option) => (
      <button
        key={option}
        onClick={() => onSelect(option)}
        disabled={isLoading}
        className="px-4 py-2 rounded-lg bg-blue-50 text-blue-900 hover:bg-blue-100 transition-colors disabled:opacity-50 border border-blue-300 text-sm font-medium hover:shadow-md"
      >
        {option}
      </button>
    ))}
  </div>
);

// Mode Selection Card Component - for welcome screen with descriptions
const ModeSelectionCard = ({
  onSelect,
  isLoading,
}: {
  onSelect: (mode: "chat" | "predict" | "simulate") => void;
  isLoading?: boolean;
}) => {
  const modes = [
    {
      id: "chat",
      title: "Chat & Get Legal Guidance",
      description: "Ask questions about legal situations, understand your rights, and receive AI-powered legal explanations and guidance.",
      icon: MessageCircle,
    },
    {
      id: "predict",
      title: "Predict Case Outcome",
      description: "Provide details about a legal case and get an AI-based prediction of the likely verdict with confidence and explanation.",
      icon: TrendingUp,
    },
    {
      id: "simulate",
      title: "Consequence Simulator",
      description: "Describe a planned action and see the potential legal consequences before you act. Understand risks and applicable laws.",
      icon: Zap,
    },
  ];

  return (
    <div className="grid grid-cols-3 gap-4 mt-4 w-full">
      {modes.map((mode) => {
        const IconComponent = mode.icon;
        return (
          <button
            key={mode.id}
            onClick={() => onSelect(mode.id as "chat" | "predict" | "simulate")}
            disabled={isLoading}
            className="group relative py-4 px-5 rounded-xl border-2 border-gray-200 bg-gradient-to-br from-white to-gray-50 hover:border-blue-400 hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed text-left hover:bg-blue-50"
          >
            <div className="flex flex-col items-start gap-2">
              <div className="p-2 rounded-lg bg-blue-100 group-hover:bg-blue-200 transition-colors">
                <IconComponent className="w-5 h-5 text-blue-600" />
              </div>
              <div className="flex-1 w-full">
                <h3 className="font-bold text-base text-foreground group-hover:text-blue-700 transition-colors">
                  {mode.title}
                </h3>
                <p className="text-xs text-muted-foreground mt-1 leading-snug">
                  {mode.description}
                </p>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
};

// Map UI-friendly case type names to backend values
const mapCaseTypeToBackend = (uiCaseType: string): string => {
  const caseTypeMap: Record<string, string> = {
    "Criminal Complaint": "criminal_complaint",
    "Property Dispute": "property_dispute",
    "Dowry Harassment": "dowry_harassment",
    "Harassment (Civil)": "harassment_civil",
    "Divorce (Contested)": "divorce_contested",
    "Divorce (Mutual Consent)": "divorce_mutual",
    "Writ Petition": "writ_petition",
    "Appeal": "appeal",
  };
  return caseTypeMap[uiCaseType] || uiCaseType.toLowerCase().replace(/\s+/g, "_");
};

const PredictionResultDisplay = ({ prediction }: { prediction: any }) => (
  <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300 rounded-lg p-4 mt-3 space-y-3">
    <div className="flex items-center gap-2">
      <CheckCircle2 className="w-5 h-5 text-green-600" />
      <h3 className="font-bold text-green-900">Case Outcome Prediction</h3>
    </div>

    <div className="grid grid-cols-2 gap-4">
      <div>
        <p className="text-sm text-green-700 font-medium">Predicted Verdict</p>
        <p className="text-lg font-bold text-green-900">{prediction.verdict}</p>
      </div>
      <div>
        <p className="text-sm text-green-700 font-medium">Confidence</p>
        <p className="text-lg font-bold text-green-900">
          {(prediction.probability * 100).toFixed(1)}%
        </p>
      </div>
    </div>

    {prediction.confidence && (
      <div>
        <p className="text-sm text-green-700 font-medium">Risk Level</p>
        <p className="text-foreground">{prediction.confidence.level}</p>
      </div>
    )}

    {prediction.recommendations && prediction.recommendations.length > 0 && (
      <div>
        <p className="text-sm text-green-700 font-medium mb-2">Recommendations</p>
        <ul className="space-y-1">
          {prediction.recommendations.slice(0, 3).map((rec: string, idx: number) => (
            <li key={idx} className="text-sm text-foreground flex items-start gap-2">
              <span className="text-green-600 mt-1">•</span>
              <span>{rec}</span>
            </li>
          ))}
        </ul>
      </div>
    )}
  </div>
);

const ChatNewV2 = () => {
  // Window scroll initialization
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, []);

  // State management
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      text: "Welcome to Smart Legal Assistant",
      sender: "bot",
      timestamp: new Date(),
      type: "options",
      data: {
        options: ["Chat & Get Legal Guidance", "Predict Case Outcome", "Consequence Simulator"],
      },
    },
  ]);

  const [mode, setMode] = useState<"chat" | "predict" | "simulate" | null>(null);
  const [caseContext, setCaseContext] = useState<CaseContext>({});
  const [currentStep, setCurrentStep] = useState(0);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle mode selection (welcome screen)
  const handleModeSelection = async (selectedMode: "chat" | "predict" | "simulate") => {
    setMode(selectedMode);

    // Add user selection to messages
    const modeText = selectedMode === "chat" ? "Chat & Get Legal Guidance" : selectedMode === "predict" ? "Predict Case Outcome" : "Consequence Simulator";
    const userMsg: Message = {
      id: Date.now().toString(),
      text: modeText,
      sender: "user",
      timestamp: new Date(),
      type: "text",
    };
    setMessages((prev) => [...prev, userMsg]);

    if (selectedMode === "chat") {
      // Chat mode - show instructions
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: "Great! 📚 I'm here to help you with legal questions. Ask me anything about your legal situation, rights, or any legal matter. I can provide guidance on various areas of law.",
        sender: "bot",
        timestamp: new Date(),
        type: "text",
      };
      setMessages((prev) => [...prev, botMsg]);
    } else if (selectedMode === "predict") {
      // Prediction mode - start guided questions
      setCurrentStep(0);
      const firstQuestion = PREDICTION_STEPS[0];

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: firstQuestion.question,
        sender: "bot",
        timestamp: new Date(),
        type: firstQuestion.type as any,
        data: {
          fieldName: firstQuestion.fieldName,
          inputType: firstQuestion.type,
          options: firstQuestion.options,
        },
      };
      setMessages((prev) => [...prev, botMsg]);
    } else if (selectedMode === "simulate") {
      // Simulate mode - ask for planned action
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: "⚡ Consequence Simulator\n\nDescribe your planned action or what you want to do. I'll analyze the potential legal consequences and risks based on applicable laws.\n\nFor example: 'I want to record a phone call with my business partner' or 'What happens if I don't pay my property taxes?'",
        sender: "bot",
        timestamp: new Date(),
        type: "text",
      };
      setMessages((prev) => [...prev, botMsg]);
    }
  };

  // Handle chat mode - send query to backend
  const handleChatMessage = async (query: string) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      text: query,
      sender: "user",
      timestamp: new Date(),
      type: "text",
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setIsLoading(true);

    try {
      const response = await fetch(`${apiUrl}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (response.ok) {
        const data = await response.json();
        const botMsg: Message = {
          id: (Date.now() + 1).toString(),
          text: data.summary || "I'll help you with this legal matter.",
          sender: "bot",
          timestamp: new Date(),
          type: "text",
        };
        setMessages((prev) => [...prev, botMsg]);
      } else {
        throw new Error("Query failed");
      }
    } catch (error) {
      console.error("Chat error:", error);
    }
  };

  // Handle simulate mode - send query to consequence simulator
  const handleSimulateMessage = async (query: string) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      text: query,
      sender: "user",
      timestamp: new Date(),
      type: "text",
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setIsLoading(true);

    // Add analyzing message
    const analyzingMsg: Message = {
      id: (Date.now() + 1).toString(),
      text: "⚙️ Analyzing consequences and legal risks...",
      sender: "bot",
      timestamp: new Date(),
      type: "text",
    };
    setMessages((prev) => [...prev, analyzingMsg]);

    try {
      const response = await fetch(`${apiUrl}/chatbot/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, mode: "simulate" }),
      });

      if (response.ok) {
        const data = await response.json();
        
        // Create a formatted response message
        let responseText = data.response || "Unable to generate analysis";
        
        if (data.risk_level || data.risk_score) {
          responseText += `\n\n📊 Risk Level: ${data.risk_level} (Score: ${data.risk_score}/100)`;
        }
        
        if (data.applicable_laws && data.applicable_laws.length > 0) {
          responseText += `\n\n⚖️ Applicable Laws:\n${data.applicable_laws.map((law: string) => `• ${law}`).join("\n")}`;
        }
        
        if (data.consequences && data.consequences.length > 0) {
          responseText += `\n\n⚠️ Potential Consequences:\n${data.consequences.map((cons: string) => `• ${cons}`).join("\n")}`;
        }
        
        if (data.prevention_suggestions && data.prevention_suggestions.length > 0) {
          responseText += `\n\n✅ How to Stay Compliant:\n${data.prevention_suggestions.map((sug: string) => `• ${sug}`).join("\n")}`;
        }

        const botMsg: Message = {
          id: (Date.now() + 1).toString(),
          text: responseText,
          sender: "bot",
          timestamp: new Date(),
          type: "text",
        };
        setMessages((prev) => [...prev, botMsg]);
      } else {
        throw new Error("Analysis failed");
      }
    } catch (error) {
      console.error("Simulate error:", error);
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: "Sorry, I couldn't analyze the consequences. Please try again.",
        sender: "bot",
        timestamp: new Date(),
        type: "text",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle prediction step answer
  const handlePredictionAnswer = async (answer: string | number | boolean) => {
    const currentStepConfig = PREDICTION_STEPS[currentStep];

    // Add user answer to messages
    let displayAnswer = answer.toString();
    if (currentStepConfig.type === "appeal_option") {
      displayAnswer = answer.toString();
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      text: displayAnswer,
      sender: "user",
      timestamp: new Date(),
      type: "text",
    };
    setMessages((prev) => [...prev, userMsg]);

    // Update context - apply mapping for case_type field and handle appeal option
    let processedValue: any = answer;
    if (currentStepConfig.fieldName === "case_type" && typeof answer === "string") {
      processedValue = mapCaseTypeToBackend(answer);
    } else if (currentStepConfig.fieldName === "is_appeal" && typeof answer === "string") {
      // Map appeal option to boolean: "Appeal or Review" -> true, "Original Case" -> false
      processedValue = answer === "Appeal or Review" ? true : false;
    }

    const updatedContext = {
      ...caseContext,
      [currentStepConfig.fieldName]: processedValue,
    };
    setCaseContext(updatedContext);

    // Move to next step or predict
    if (currentStep < PREDICTION_STEPS.length - 1) {
      // More questions
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);

      const nextStepConfig = PREDICTION_STEPS[nextStep];
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: nextStepConfig.question,
        sender: "bot",
        timestamp: new Date(),
        type: nextStepConfig.type as any,
        data: {
          fieldName: nextStepConfig.fieldName,
          inputType: nextStepConfig.type,
          options: nextStepConfig.options,
        },
      };
      setMessages((prev) => [...prev, botMsg]);
    } else {
      // All questions answered - call predict API
      await callPredictAPI(updatedContext);
    }

    setInputText("");
  };

  // Call case outcome prediction API
  const callPredictAPI = async (context: CaseContext) => {
    setIsLoading(true);

    // Add processing message
    const processingMsg: Message = {
      id: Date.now().toString(),
      text: "🔍 Analyzing your case and generating prediction...",
      sender: "bot",
      timestamp: new Date(),
      type: "text",
    };
    setMessages((prev) => [...prev, processingMsg]);

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

      if (response.ok) {
        const prediction = await response.json();

        // Add prediction result message
        const resultMsg: Message = {
          id: (Date.now() + 1).toString(),
          text: `Prediction for: ${context.case_name}`,
          sender: "bot",
          timestamp: new Date(),
          type: "prediction_result",
          data: { prediction },
        };
        setMessages((prev) => [...prev, resultMsg]);

        // Add follow-up message
        const followupMsg: Message = {
          id: (Date.now() + 2).toString(),
          text: "Would you like to ask any legal questions about this case, or would you like to start a new prediction?",
          sender: "bot",
          timestamp: new Date(),
          type: "text",
        };
        setMessages((prev) => [...prev, followupMsg]);
      } else {
        throw new Error("Prediction failed");
      }
    } catch (error) {
      console.error("Prediction error:", error);
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: "Sorry, I couldn't generate the prediction. Please try again.",
        sender: "bot",
        timestamp: new Date(),
        type: "text",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  // Main send handler
  const handleSend = () => {
    if (!inputText.trim()) return;

    if (mode === "chat") {
      handleChatMessage(inputText);
    } else if (mode === "simulate") {
      handleSimulateMessage(inputText);
    } else if (mode === "predict" && currentStep < PREDICTION_STEPS.length) {
      const currentStepConfig = PREDICTION_STEPS[currentStep];

      // Validate input based on type
      if (currentStepConfig.type === "numeric_input") {
        const numValue = parseFloat(inputText);
        if (isNaN(numValue)) {
          alert("Please enter a valid number");
          return;
        }
        handlePredictionAnswer(numValue);
      } else if (currentStepConfig.type === "text_input") {
        if (inputText.trim().length === 0) {
          alert("Please enter a value");
          return;
        }
        handlePredictionAnswer(inputText.trim());
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Render message content based on type
  const renderMessageContent = (message: Message) => {
    switch (message.type) {
      case "options":
        // Check if this is a mode selection (welcome screen) vs prediction question
        if (message.data?.options?.includes("Chat & Get Legal Guidance")) {
          // Mode selection - render with ModeSelectionCard
          return <ModeSelectionCard onSelect={handleModeSelection} isLoading={isLoading} />;
        }
        // Regular option buttons
        return (
          <div>
            <p className="text-sm mb-3">{message.text}</p>
            {message.data?.options && (
              <OptionButtons
                options={message.data.options}
                onSelect={(option) => handlePredictionAnswer(option)}
                isLoading={isLoading}
              />
            )}
          </div>
        );

      case "appeal_option":
        return (
          <div>
            <p className="text-sm mb-3">{message.text}</p>
            {message.data?.options && (
              <OptionButtons
                options={message.data.options}
                onSelect={(option) => handlePredictionAnswer(option)}
                isLoading={isLoading}
              />
            )}
          </div>
        );

      case "prediction_result":
        return (
          message.data?.prediction && <PredictionResultDisplay prediction={message.data.prediction} />
        );

      default:
        return <p className="text-sm whitespace-pre-wrap">{message.text}</p>;
    }
  };

  // Input placeholder based on current state
  const getInputPlaceholder = (): string => {
    if (mode === "simulate") return "Describe your planned action...";
    if (!mode) return "Select an option...";
    if (mode === "chat") return "Ask a legal question...";

    const currentStepConfig = PREDICTION_STEPS[currentStep];
    if (currentStepConfig?.type === "text_input") return "Enter case name...";
    if (currentStepConfig?.type === "numeric_input") return "Enter a number...";
    return "Your answer...";
  };

  // Check if should show input or options
  const lastMessage = messages[messages.length - 1];
  const shouldShowOptions =
    lastMessage?.type === "options" && lastMessage?.data?.options
      ? lastMessage.data.options
      : null;

  const shouldShowNumericInput =
    lastMessage?.type === "numeric_input" &&
    PREDICTION_STEPS[currentStep]?.type === "numeric_input";

  const shouldShowAppealOption =
    lastMessage?.type === "appeal_option";

  return (
    <Layout>
      <div className="min-h-[calc(100vh-200px)] flex flex-col bg-gradient-to-br from-blue-50 via-white to-purple-50 py-8">
        <div className="container mx-auto px-4 max-w-3xl flex-1 flex flex-col">
          {/* Header */}
          <div className="text-center mb-6 animate-fade-up">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
              Smart Legal Assistant
            </h1>
            <p className="text-lg text-muted-foreground">
              Chat for guidance or predict case outcomes with AI-powered analysis
            </p>
          </div>

          {/* Chat Container */}
          <div className="flex-1 flex flex-col rounded-2xl border-2 border-gray-200 bg-white shadow-xl hover:shadow-2xl transition-shadow duration-300 overflow-hidden">
            {/* Chat Messages Area */}
            <div
              ref={chatContainerRef}
              className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin scrollbar-thumb-blue-300 scrollbar-track-gray-100"
            >
              {messages.map((message, index) => (
                <div
                  key={message.id}
                  className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"} animate-fade-up`}
                  style={{ animationDelay: `${index * 0.05}s` }}
                >
                  <div
                    className={`flex max-w-[85%] ${
                      message.sender === "user" ? "flex-row-reverse" : "flex-row"
                    } items-start gap-3`}
                  >
                    {/* Avatar */}
                    <div
                      className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                        message.sender === "user"
                          ? "bg-gradient-to-br from-blue-500 to-purple-500 text-white"
                          : "bg-gradient-to-br from-green-400 to-blue-500 text-white"
                      }`}
                    >
                      {message.sender === "user" ? (
                        <User className="h-4 w-4" />
                      ) : (
                        <Bot className="h-4 w-4" />
                      )}
                    </div>

                    {/* Message bubble */}
                    <div
                      className={`rounded-2xl px-4 py-3 ${
                        message.sender === "user"
                          ? "bg-gradient-to-br from-blue-500 to-purple-600 text-white rounded-br-none shadow-md"
                          : message.type === "prediction_result"
                          ? "bg-transparent"
                          : "bg-gray-100 text-foreground rounded-bl-none shadow-sm"
                      }`}
                    >
                      {renderMessageContent(message)}
                      {message.type === "text" && (
                        <p className="text-xs mt-2 opacity-70">
                          {message.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start animate-fade-up">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-green-400 to-blue-500 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-white" />
                    </div>
                    <div className="bg-gray-100 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
                      <div className="flex space-x-2">
                        <div
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0ms" }}
                        />
                        <div
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "150ms" }}
                        />
                        <div
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "300ms" }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Section */}
            <div className="border-t border-gray-200 bg-gray-50 p-4 flex-shrink-0">
              {shouldShowOptions && mode === null ? (
                // Mode selection options - handled by ModeSelectionCard in renderMessageContent
                <div></div>
              ) : shouldShowAppealOption && mode === "predict" ? (
                // Appeal option buttons for prediction
                <OptionButtons
                  options={PREDICTION_STEPS[currentStep]?.options || []}
                  onSelect={(option) => handlePredictionAnswer(option)}
                  isLoading={isLoading}
                />
              ) : shouldShowNumericInput && mode === "predict" ? (
                // Numeric input for damages/year
                <div className="flex space-x-2">
                <input
                  type="number"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={getInputPlaceholder()}
                  className="flex-1 px-4 py-3 rounded-lg border-2 border-gray-300 bg-white text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
                <button
                  onClick={handleSend}
                  disabled={!inputText.trim() || isLoading}
                  className="inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-blue-500 to-purple-600 px-4 py-3 text-white hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {isLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Send className="h-5 w-5" />
                  )}
                </button>
              </div>
              ) : (
                // Regular text input
                <div className="flex space-x-2">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={getInputPlaceholder()}
                  disabled={isLoading}
                  className="flex-1 px-4 py-3 rounded-lg border-2 border-gray-300 bg-white text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all disabled:opacity-50"
                />
                <button
                  onClick={handleSend}
                  disabled={!inputText.trim() || isLoading}
                  className="inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-blue-500 to-purple-600 px-4 py-3 text-white hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {isLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Send className="h-5 w-5" />
                  )}
                </button>
              </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default ChatNewV2;
