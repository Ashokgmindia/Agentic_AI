import os
import logging
from datetime import datetime
from typing import Union, List
from dotenv import load_dotenv
from crewai import LLM, Agent, Crew, Process, Task
from crewai.memory import LongTermMemory, ShortTermMemory
from crewai.memory.storage.ltm_sqlite_storage import LTMSQLiteStorage
from crewai.memory.storage.rag_storage import RAGStorage
from textwrap import dedent

# Import your enhanced multimodal tools
from tools.multimodal_tools import (
    ingest_text, ingest_pdf, ingest_image, ingest_audio,
    ingest_csv, ingest_ppt, ingest_doc, ingest_xlsx,
    mcp_search, a2a_communicate
)

load_dotenv()
logger = logging.getLogger(__name__)

class StakeholderAgent:
    """Enhanced Multimodal Stakeholder Agent with web interface compatibility and A2A integration."""
    
    SUPPORTED_CONTENT_TYPES = [
        "text/plain",
        "application/pdf", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/csv",
        "image/jpeg", "image/png", "image/gif",
        "audio/wav", "audio/mp3", "audio/m4a"
    ]

    def __init__(self):
        # Load LLM (Gemini preferred, fallback to OpenAI)
        if os.getenv("GOOGLE_API_KEY"):
            self.llm = LLM(
                model="gemini/gemini-2.5-flash",
                api_key=os.getenv("GOOGLE_API_KEY")
            )
        elif os.getenv("OPENAI_API_KEY"):
            self.llm = LLM(
                model="gpt-4o-mini",
                api_key=os.getenv("OPENAI_API_KEY")
            )
        else:
            raise ValueError("Neither GOOGLE_API_KEY nor OPENAI_API_KEY environment variable is set.")

        # All multimodal tools
        self.tools = [
            ingest_text, ingest_pdf, ingest_image, ingest_audio,
            ingest_csv, ingest_ppt, ingest_doc, ingest_xlsx,
            mcp_search, a2a_communicate
        ]

        # Memory setup
        os.makedirs("./memory", exist_ok=True)
        self.long_term_memory = LongTermMemory(storage=LTMSQLiteStorage(db_path="./memory/long_term_memory.db"))
        
        # Setup short-term memory if OpenAI key available
        self.short_term_memory = None
        try:
            if os.getenv("OPENAI_API_KEY"):
                from crewai.memory.storage.rag_storage import RAGStorage
                self.short_term_memory = ShortTermMemory(storage=RAGStorage(
                    embedder_config={
                        "provider": "openai",
                        "config": {"model": "text-embedding-3-small"}
                    },
                    type="short_term",
                    path="./memory/"
                ))
        except Exception as e:
            logger.warning(f"Could not initialize short-term memory: {e}")

        # Enhanced Stakeholder Agent
        self.stakeholder_agent = Agent(
            role="GMI Stakeholder Agent",
            goal=dedent("""
                Transform rough, multimodal ideas into clear, strategic high-level visions using the GMI Advanced Agentic AI Framework.
                Coordinate with other agents via A2A protocol to ensure comprehensive analysis and validation.
                Process any input format (text, PDF, images, audio, spreadsheets) and produce execution-ready project concepts."""),
            backstory=dedent("""
                You are the primary orchestrator in the GMI Advanced Agentic AI Framework, specializing in multimodal input processing
                and strategic concept development. You have access to advanced ingestion tools for any file type and can communicate
                with specialized agents (BA General, Domain Expert, Product Manager, Agile Project Manager) through the A2A protocol.
                Your expertise lies in transforming ambiguous ideas into structured, actionable project visions that align with business objectives."""),
            tools=self.tools,
            verbose=True,
            memory=True,
            multimodal=True,
            allow_delegation=False,
            llm=self.llm
        )

    def process_web_input(self, text_input: str = None, file_path: str = None, file_type: str = None) -> str:
        """
        Process input from web interface and return stakeholder brief.
        """
        logger.info("[StakeholderAgent] Processing web interface input...")
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Prepare input context
        input_context = ""
        if text_input:
            input_context += f"Text Input: {text_input}\n"
        if file_path:
            input_context += f"File: {file_path} (Type: {file_type})\n"

        # Create task with intelligent tool routing
        stakeholder_task = Task(
            description=dedent(f"""
                 **GMI Stakeholder Agent - Comprehensive Analysis Task**

                ### Input Context:
                {input_context}

                ### Instructions:
                1. **Intelligent Tool Selection**: 
                   - For file type '{file_type}', use ONLY the corresponding ingest tool:
                     * Text files (.txt) → Use 'Ingest Text'
                     * PDF files → Use 'Ingest PDF' 
                     * Images → Use 'Ingest Image'
                     * Audio files → Use 'Ingest Audio'
                     * CSV files → Use 'Ingest CSV'
                     * PowerPoint → Use 'Ingest PPT'
                     * Word docs → Use 'Ingest DOC'
                     * Excel files → Use 'Ingest XLSX'
                   - For text input, process directly without additional tools

                2. **Content Analysis & Vision Development**:
                   - Analyze the ingested content thoroughly
                   - Identify core business objectives and opportunities
                   - Define key performance indicators (KPIs)
                   - Extract actionable insights and strategic direction

                3. **MCP Knowledge Integration**:
                   - Use 'MCP Search' to find relevant past projects and learnings
                   - Incorporate best practices and risk mitigation strategies
                   - Benchmark against similar successful implementations

                4. **A2A Collaboration** (simulate coordination):
                   - Query Domain Expert for compliance and feasibility via 'A2A Communication'
                   - Coordinate with BA General for requirements validation
                   - Align with Product Manager on strategic direction

                5. **Stakeholder Brief Generation**:
                   - Create a comprehensive, professional stakeholder brief
                   - Structure it according to GMI framework standards
                   - Include clear next steps and handoff instructions

                **Expected Output**: A complete Stakeholder Brief that transforms the input into an execution-ready project concept.
                """),
            expected_output=dedent(f"""
                 # GMI Stakeholder Brief: [Project Title]

                ## Executive Summary
                A concise overview of the transformed project concept with clear value proposition.

                ## 1. Strategic Vision
                - **Vision Statement**: Clear, compelling project vision
                - **Business Objectives**: Primary goals and expected outcomes
                - **Success Metrics**: Specific, measurable KPIs

                ## 2. Content Analysis Results
                - **Input Summary**: What was analyzed and key findings
                - **Core Insights**: Strategic insights derived from the content
                - **Opportunity Assessment**: Market and business opportunities identified

                ## 3. A2A Collaboration Results
                - Query Business Analyst Domain Expert Agent for compliance and feasibility via 'A2A Communication'
                - Coordinate with Business Analyst Agent for requirements validation
                - Align with Product Manager Agent on strategic direction

                ## 4. MCP Knowledge Integration
                - **Relevant Past Projects**: Similar projects and their outcomes
                - **Best Practices**: Proven strategies and approaches
                - **Risk Mitigation**: Potential challenges and prevention strategies

                ## 5. Implementation Roadmap
                - **Immediate Next Steps**: Actions for the next phase
                - **Resource Requirements**: Team and technology needs
                - **Timeline Expectations**: High-level schedule estimates

                ## 6. Handoff to Next Stage
                - **Ready for**: Business Analyst (General) detailed requirements gathering
                - **Key Documents**: Stakeholder Brief, analysis results, A2A communication logs
                - **Success Criteria**: Criteria for next phase approval

                ---
                *Generated by GMI Advanced Agentic AI Framework | Stakeholder Agent**
                """),
            agent=self.stakeholder_agent,
            tools=self.tools,
            output_file="output/stakeholder_brief.md"
        )

        # Execute the task with memory
        crew_config = {
            "agents": [self.stakeholder_agent],
            "tasks": [stakeholder_task],
            "process": Process.sequential,
            "verbose": True,
            "long_term_memory": self.long_term_memory,
        }
        
        if self.short_term_memory is not None:
            crew_config["short_term_memory"] = self.short_term_memory

        crew = Crew(**crew_config)
        
        try:
            result = crew.kickoff()
            return str(result)
        except Exception as e:
            logger.error(f"[StakeholderAgent] Error in processing: {e}")
            return f"Sorry, I encountered an error processing your request: {str(e)}"

    def invoke(self, stakeholder_inputs: Union[str, List[str]]) -> str:
        """
        Standard invoke method for A2A compatibility.
        """
        logger.info("[StakeholderAgent] Starting A2A invoke method...")
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Process A2A input
        stakeholder_task = Task(
            description=f"""
            Process the stakeholder input and generate a comprehensive stakeholder brief.
            Input: {stakeholder_inputs}
            
            Use appropriate multimodal tools for analysis and create a detailed stakeholder brief ready for Business Analyst processing.
            """,
            expected_output=f"""Complete GMI Stakeholder Brief with strategic vision and implementation roadmap ready for A2A handoff to Business Analyst Agent. Generated on {current_date}.""",
            agent=self.stakeholder_agent,
            tools=self.tools,
            output_file="output/stakeholder_brief.md"
        )

        crew_config = {
            "agents": [self.stakeholder_agent],
            "tasks": [stakeholder_task],
            "process": Process.sequential,
            "verbose": True,
            "long_term_memory": self.long_term_memory,
        }
        
        if self.short_term_memory is not None:
            crew_config["short_term_memory"] = self.short_term_memory

        crew = Crew(**crew_config)

        try:
            # Execute stakeholder analysis
            stakeholder_result = crew.kickoff(inputs={"stakeholder_inputs": stakeholder_inputs})
            stakeholder_brief = str(stakeholder_result)
            
            logger.info("[StakeholderAgent] Stakeholder analysis complete, starting A2A handoffs...")
            
            # Automated A2A handoffs to other agents
            ba_response = a2a_communicate("BA_General", stakeholder_brief)
            if "error" not in ba_response:
                logger.info("[StakeholderAgent] Business Analyst processing complete")
                
                domain_response = a2a_communicate("Domain_Expert", ba_response.get("response_received", stakeholder_brief))
                if "error" not in domain_response:
                    logger.info("[StakeholderAgent] Domain Expert validation complete")
                    
                    pm_response = a2a_communicate("Product_Manager", domain_response.get("response_received", stakeholder_brief))
                    if "error" not in pm_response:
                        logger.info("[StakeholderAgent] Product Manager roadmap complete")
                        
                        agile_response = a2a_communicate("Agile_Project_Manager", pm_response.get("response_received", stakeholder_brief))
                        if "error" not in agile_response:
                            logger.info("[StakeholderAgent] Complete GMI pipeline executed successfully!")
                            
                            # Return complete pipeline summary
                            final_result = agile_response.get("response_received", stakeholder_brief)
                            return f"""# GMI Complete Pipeline Results

## Pipeline Execution Summary
- **Started**: {current_date}
- **Pipeline Status**: ✅ COMPLETED SUCCESSFULLY
- **Agents Processed**: Stakeholder → Business Analyst → Domain Expert → Product Manager → Agile PM

---

## Final Project Execution Plan

{final_result}

---

## Processing Trail
1. **Stakeholder Agent**: Initial analysis and vision development ✅
2. **Business Analyst**: Requirements documentation ✅  
3. **Domain Expert**: Compliance and feasibility validation ✅
4. **Product Manager**: Strategic roadmap development ✅
5. **Agile Project Manager**: Execution planning ✅

*Generated by GMI Advanced Agentic AI Framework | Complete Pipeline*
"""
            
            # Return stakeholder brief if handoffs fail
            return stakeholder_brief
            
        except Exception as e:
            logger.error(f"[StakeholderAgent] Pipeline execution failed: {e}")
            return f"Sorry, the GMI pipeline encountered an error: {str(e)}. Please try again."

# For backward compatibility and testing
if __name__ == "__main__":
    agent = StakeholderAgent()
    output = agent.invoke("We need a time management app for business executives")
    print(output)
