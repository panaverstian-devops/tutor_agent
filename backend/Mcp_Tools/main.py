"""
Pdf Reader For MCP — with streamable HTTP app and student/course mock data

Features:
 - Provides PDFReader for extracting text/search.
 - Provides make_pdf_tool and register_pdf_tool.
 - Registers two tools: pdf_reader_computer7 and pdf_reader_english7.
 - Includes FastMCP integration and exposes streamable_http_app.
 - Provides mock STUDENTS, COURSES, TOPICS data for tutoring context.
 - Tools for fetching student profile, courses, TOC, personalized content.
 - Includes tests and demo.
"""

from __future__ import annotations
import os
import sys
import tempfile
from typing import Dict, Any, Optional, Callable

try:
    from PyPDF2 import PdfReader, PdfWriter
except Exception as e:
    raise ImportError("PyPDF2 is required. Install it with: pip install PyPDF2") from e

# -----------------------------
# Mock Data
# -----------------------------
STUDENTS: Dict[str, Any] = {
    "muhammad": {
        "name": "Muhammad Mustafa",
        "level": "beginner",
        "style": "visual",
        "active_cursor_position": {
            "course_id": "CS-7",
            "topic_id": "cs_unit1_topic1"
        }
    },
    "fatima": {
        "name": "Fatima Noor",
        "level": "intermediate",
        "style": "auditory",
        "active_cursor_position": {
            "course_id": "EN-7",
            "topic_id": "en_unit1_topic1"
        }
    },
    "ali": {
        "name": "Ali Khan",
        "level": "advanced",
        "style": "kinesthetic",
        "active_cursor_position": {
            "course_id": "CS-7",
            "topic_id": "cs_unit2_topic1"
        }
    },
}

COURSES: Dict[str, Any] = {
    "CS-7": {
        "title": "Computer Science Grade 7 (SNC 2023-24)",
        "toc": [
            {"name": "cs_unit1", "description": "Emerging Technologies"},
            {"name": "cs_unit2", "description": "Digital Skills"},
            {"name": "cs_unit3", "description": "Computational Thinking"},
            {"name": "cs_unit4", "description": "Programming"},
            {"name": "cs_unit5", "description": "Digital Citizenship"},
            {"name": "cs_unit6", "description": "Entrepreneurship in Digital Age"},
        ]
    },
    "EN-7": {
        "title": "English Grade 7 (SNC 2023-24)",
        "toc": [
            {"name": "en_unit1", "description": "Reading and Literature"},
            {"name": "en_unit2", "description": "Writing Skills"},
            {"name": "en_unit3", "description": "Grammar and Language"},
            {"name": "en_unit4", "description": "Speaking and Listening"},
            {"name": "en_unit5", "description": "Vocabulary Development"},
            {"name": "en_unit6", "description": "Creative Expression"},
        ]
    },
}

TOPICS: Dict[str, Any] = {
    "cs_unit1_topic1": {
        "title": "Introduction to Emerging Technologies",
        "content": "Understanding what emerging technologies are and their impact on society.",
        "topic_id": "cs_unit1_topic1",
        "unit": "cs_unit1",
        "content_resource_urls": {}
    },
    "cs_unit2_topic1": {
        "title": "Digital Literacy Fundamentals",
        "content": "Essential skills for navigating digital environments.",
        "topic_id": "cs_unit2_topic1",
        "unit": "cs_unit2",
        "content_resource_urls": {}
    },
    "en_unit1_topic1": {
        "title": "Reading Strategies and Comprehension",
        "content": "Techniques for understanding and analyzing texts.",
        "topic_id": "en_unit1_topic1",
        "unit": "en_unit1",
        "content_resource_urls": {}
    }
}

# -----------------------------
# PDF Reader Implementation
# -----------------------------
class PDFReader:
    def __init__(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"PDF not found: {path}")
        self.path = path
        self.reader = PdfReader(path)

    def num_pages(self) -> int:
        return len(self.reader.pages)

    def get_page_text(self, page_number: int) -> str:
        if page_number < 0 or page_number >= self.num_pages():
            raise IndexError("Page number out of range")
        return self.reader.pages[page_number].extract_text() or ""

    def get_all_text(self) -> str:
        return "\n\n".join([(p.extract_text() or "") for p in self.reader.pages])

    def search(self, query: str) -> list[Dict[str, Any]]:
        q = (query or "").lower()
        hits: list[Dict[str, Any]] = []
        for i, p in enumerate(self.reader.pages):
            text = p.extract_text() or ""
            low = text.lower()
            if q and q in low:
                idx = low.index(q)
                start = max(0, idx - 40)
                end = min(len(text), idx + len(q) + 40)
                snippet = text[start:end].replace('\n', ' ')
                hits.append({"page": i, "snippet": snippet})
        return hits

def create_blank_pdf(path: str, num_pages: int = 1) -> None:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as f:
        writer.write(f)

def make_pdf_tool(pdf_path: str) -> Callable[[Dict[str, Any]], Any]:
    reader: Optional[PDFReader] = None

    def tool(params: Dict[str, Any]) -> Any:
        nonlocal reader
        if reader is None:
            try:
                reader = PDFReader(pdf_path)
            except FileNotFoundError as e:
                return {"error": "pdf_not_found", "message": str(e), "pdf_path": pdf_path}
            except Exception as e:
                return {"error": "failed_open_pdf", "exception": str(e), "pdf_path": pdf_path}

        action = params.get("action", "get_all")
        try:
            if action == "get_page":
                page = int(params.get("page", 0))
                try:
                    return {"result": reader.get_page_text(page)}
                except IndexError as ie:
                    return {"error": "page_out_of_range", "message": str(ie)}
            elif action == "get_all":
                return {"result": reader.get_all_text()}
            elif action == "search":
                q = params.get("query", "")
                return {"result": reader.search(q)}
            else:
                return {"error": "unknown_action", "action": action}
        except Exception as e:
            return {"error": "tool_execution_error", "exception": str(e)}

    return tool

def register_pdf_tool(agent: Any, pdf_path: str, tool_name: str) -> str:
    tool_callable = make_pdf_tool(pdf_path)
    agent.register_tool(tool_name, tool_callable)
    return tool_name

PDF_PATHS: Dict[str, str] = {
    "computer7": r"backend/Mcp_Tools/Computer 7 SNC 2023-24 (1).pdf",
    "english7": r"backend/Mcp_Tools/English 7 SNC 2023-24.pdf",
}

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore

    mcp_app: FastMCP = FastMCP(name="STUDY_MODE_TOOLBOX", stateless_http=True)

    # PDF Path setter tool
    @mcp_app.tool()
    def set_pdf_path(key: str, path: str, auth_token: str = None) -> Dict[str, Any]:
        """Set PDF path for a named key"""
        if not key:
            return {"error": "missing_key"}
        PDF_PATHS[key] = path
        return {"ok": True, "key": key, "path": path}

    # Student-related tools
    @mcp_app.tool()
    def get_student_profile(user_id: str, auth_token: str = None) -> Dict[str, Any]:
        """Get basic student information for teaching"""
        if user_id in STUDENTS:
            return STUDENTS[user_id]
        raise ValueError(f"Student {user_id} not found")

    @mcp_app.tool()
    def get_course_basic_info(course_id: str, auth_token: str = None) -> Dict[str, Any]:
        """Get basic course information"""
        if course_id in COURSES:
            return COURSES[course_id]
        raise ValueError(f"Course {course_id} not found")

    @mcp_app.tool()
    def get_table_of_contents(course_id: str, auth_token: str = None) -> Dict[str, Any]:
        """Get course modules list"""
        if course_id in COURSES:
            toc = COURSES[course_id]["toc"]
            result = {"course_id": course_id, "total_modules": len(toc)}
            for i, module in enumerate(toc):
                result[f"module_{i}"] = f"{module['name']}: {module['description']}"
            return result
        raise ValueError(f"Course {course_id} not found")

    @mcp_app.tool()
    def get_current_topic(user_id: str, auth_token: str = None) -> Dict[str, Any]:
        """Get student's current topic"""
        if user_id in STUDENTS:
            student = STUDENTS[user_id]
            topic_id = student["active_cursor_position"]["topic_id"]
            topic = TOPICS.get(topic_id, {})
            return {
                "topic_id": topic_id,
                "topic_details": topic,
                "student": student,
            }
        raise ValueError(f"Student {user_id} not found")

    # PDF Reader tools
    @mcp_app.tool()
    def pdf_reader_computer7(action: str = "get_all", page: int = 0, query: str = "") -> Dict[str, Any]:
        """Read Computer Science Grade 7 PDF content"""
        return make_pdf_tool(PDF_PATHS["computer7"])({"action": action, "page": page, "query": query})

    @mcp_app.tool()
    def pdf_reader_english7(action: str = "get_all", page: int = 0, query: str = "") -> Dict[str, Any]:
        """Read English Grade 7 PDF content"""
        return make_pdf_tool(PDF_PATHS["english7"])({"action": action, "page": page, "query": query})

    # Streamable HTTP app
    app = mcp_app.streamable_http_app()

except Exception as e:
    print("FastMCP integration skipped:", e)
    app = None

# -----------------------------
# Mock Agent + Tests
# -----------------------------
class _MockAgent:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register_tool(self, name: str, func: Callable):
        if name in self._tools:
            raise ValueError(f"Tool '{name}' already registered")
        self._tools[name] = func

    def call_tool(self, name: str, params: Dict[str, Any]):
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        return self._tools[name](params)

def run_tests() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pdf = os.path.join(tmpdir, "test.pdf")
        create_blank_pdf(tmp_pdf, num_pages=2)
        reader = PDFReader(tmp_pdf)
        assert reader.num_pages() == 2
        assert isinstance(reader.get_page_text(0), str)
        assert isinstance(reader.get_all_text(), str)
        assert isinstance(reader.search("anything"), list)

    missing_path = os.path.join(tempfile.gettempdir(), "non_existent.pdf")
    tool = make_pdf_tool(missing_path)
    result = tool({"action": "get_all"})
    assert result.get("error") == "pdf_not_found"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pdf = os.path.join(tmpdir, "t2.pdf")
        create_blank_pdf(tmp_pdf, num_pages=1)
        agent = _MockAgent()
        register_pdf_tool(agent, tmp_pdf, "t2_pdf")
        res = agent.call_tool("t2_pdf", {"action": "get_all"})
        assert "result" in res

def demo_usage() -> None:
    agent = _MockAgent()
    register_pdf_tool(agent, PDF_PATHS["computer7"], "pdf_reader_computer7")
    register_pdf_tool(agent, PDF_PATHS["english7"], "pdf_reader_english7")
    print(agent.call_tool("pdf_reader_computer7", {"action": "get_all"}))
    print(agent.call_tool("pdf_reader_english7", {"action": "search", "query": "lesson"}))

if __name__ == "__main__":
    if "--run-tests" in sys.argv:
        run_tests()
    elif "--demo" in sys.argv:
        demo_usage()
    else:
        # Start the MCP server
        if app is not None:
            print("🚀 Starting MCP Server for Student Data and Content Access...")
            print("=" * 60)
            print("Server will be available at: http://localhost:8000/mcp")
            print("Press Ctrl+C to stop the server")
            print("=" * 60)
            
            import uvicorn
            uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
        else:
            print("❌ MCP server not available. Check FastMCP installation.")
            print("Installing required packages...")
            print("Run: pip install fastmcp uvicorn")
            demo_usage()
