#!/usr/bin/env python3
"""
Enhanced Learning Pack Generator
Uses MCP tools to get book content and generate comprehensive learning packs.
"""

import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from agents import AsyncOpenAI, OpenAIChatCompletionsModel, Runner, Agent
from agents.mcp import MCPServerStreamableHttp

class EnhancedLearningPackGenerator:
    """Enhanced generator that uses MCP tools for book content"""
    
    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        self.model = None
        self.mcp_servers = []
        
        if self.openai_api_key:
            try:
                self.client = AsyncOpenAI(api_key=self.openai_api_key)
                self.model = OpenAIChatCompletionsModel(
                    model="gpt-3.5-turbo",
                    openai_client=self.client
                )
            except Exception as e:
                print(f"⚠️ OpenAI connection failed: {e}")
    
    async def setup_mcp_servers(self):
        """Set up MCP servers for book content access"""
        try:
            # Local MCP Server for student data and content
            local_mcp_params = {
                "url": "http://localhost:8000/mcp",
                "timeout": 10,
            }
            
            self.local_server = MCPServerStreamableHttp(
                name="StudentDataToolbox",
                params=local_mcp_params,
                cache_tools_list=True,
                max_retry_attempts=3,
            )
            
            await self.local_server.connect()
            self.mcp_servers.append(self.local_server)
            print("✅ Connected to local MCP server for book content")
            
        except Exception as e:
            print(f"⚠️ Could not connect to MCP server: {e}")
            print("🔄 Continuing without MCP server...")
    
    async def get_book_content(self, subject: str, chapter: int) -> Dict[str, Any]:
        """Get book content using MCP tools"""
        if not self.mcp_servers:
            return None
        
        try:
            # Create a temporary agent with MCP tools
            book_agent = Agent(
                name="BookContentAgent",
                instructions=f"""
                You are a book content extraction agent. Use the available MCP tools to get content for {subject} Chapter {chapter}.
                
                Your task:
                1. Use the PDF reading tools to get chapter content
                2. Extract key concepts, examples, and exercises
                3. Format the content for learning pack generation
                
                Return structured content with:
                - Chapter title
                - Key concepts (3-5 main points)
                - Detailed explanations
                - Examples and exercises
                - Summary
                """,
                model=self.model,
                mcp_servers=self.mcp_servers
            )
            
            # Get content using the agent
            response = await Runner.run(
                starting_agent=book_agent,
                input=f"Extract content for {subject} Chapter {chapter} from available books and resources."
            )
            
            # Parse the response to extract structured content
            content_text = response.final_output if hasattr(response, 'final_output') else str(response)
            
            # Structure the content
            return {
                "title": f"{subject} - Chapter {chapter}",
                "overview": f"Chapter {chapter} of {subject} covering essential concepts.",
                "key_concepts": self._extract_key_concepts(content_text),
                "detailed_content": content_text,
                "examples": self._extract_examples(content_text),
                "summary": self._generate_summary(content_text)
            }
            
        except Exception as e:
            print(f"⚠️ Error getting book content: {e}")
            return None
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """Extract key concepts from content"""
        # Simple extraction - in real implementation, use more sophisticated parsing
        lines = content.split('\n')
        concepts = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['concept', 'principle', 'theory', 'method', 'technique']):
                if len(line.strip()) > 10 and len(line.strip()) < 100:
                    concepts.append(line.strip())
                    if len(concepts) >= 5:
                        break
        
        # Fallback if no concepts found
        if not concepts:
            concepts = [
                "Fundamental concepts and principles",
                "Key theories and methods",
                "Practical applications",
                "Problem-solving techniques",
                "Advanced topics and extensions"
            ]
        
        return concepts[:5]
    
    def _extract_examples(self, content: str) -> List[str]:
        """Extract examples from content"""
        # Simple extraction - in real implementation, use more sophisticated parsing
        lines = content.split('\n')
        examples = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['example', 'for instance', 'such as', 'case study']):
                if len(line.strip()) > 15 and len(line.strip()) < 150:
                    examples.append(line.strip())
                    if len(examples) >= 3:
                        break
        
        # Fallback if no examples found
        if not examples:
            examples = [
                "Real-world application example",
                "Step-by-step problem solving",
                "Practical implementation case"
            ]
        
        return examples[:3]
    
    def _generate_summary(self, content: str) -> str:
        """Generate a summary of the content"""
        # Simple summary generation
        sentences = content.split('.')
        summary_sentences = []
        
        for sentence in sentences[:3]:
            if len(sentence.strip()) > 20:
                summary_sentences.append(sentence.strip())
        
        if summary_sentences:
            return '. '.join(summary_sentences) + '.'
        else:
            return "This chapter covers essential concepts and provides practical examples for better understanding."
    
    async def generate_enhanced_learning_pack(self, subject: str, chapter_number: int, student_level: str = "beginner") -> Dict[str, Any]:
        """Generate enhanced learning pack using MCP tools"""
        
        print(f"📚 Generating enhanced learning pack for {subject} - Chapter {chapter_number}")
        
        # Set up MCP servers
        await self.setup_mcp_servers()
        
        # Get book content using MCP tools
        book_content = await self.get_book_content(subject, chapter_number)
        
        # Generate study material (use book content if available)
        if book_content:
            study_material = book_content
            print("✅ Using book content from MCP tools")
        else:
            study_material = await self._generate_fallback_study_material(subject, chapter_number, student_level)
            print("⚠️ Using fallback content (MCP tools not available)")
        
        # Generate assessment quiz
        quiz = await self._generate_enhanced_quiz(subject, chapter_number, study_material)
        
        # Create learning pack structure
        learning_pack = {
            "pack_info": {
                "pack_id": f"{subject.lower()}_ch{chapter_number:03d}",
                "subject": subject,
                "chapter_number": chapter_number,
                "title": study_material.get("title", f"{subject} - Chapter {chapter_number}"),
                "created_date": datetime.now().isoformat(),
                "expires_date": (datetime.now() + timedelta(days=1)).isoformat(),
                "student_level": student_level,
                "status": "ready",
                "source": "MCP_Book_Content" if book_content else "Generated_Content"
            },
            "study_material": study_material,
            "assessment": quiz,
            "progress": {
                "completed": False,
                "score": None,
                "time_spent": 0,
                "last_accessed": None
            }
        }
        
        return learning_pack
    
    async def _generate_fallback_study_material(self, subject: str, chapter_number: int, student_level: str) -> Dict[str, Any]:
        """Generate fallback study material when MCP tools are not available"""
        
        if not self.client:
            return {
                "title": f"{subject} - Chapter {chapter_number}",
                "overview": f"This chapter covers fundamental concepts in {subject}.",
                "key_concepts": ["Concept 1", "Concept 2", "Concept 3"],
                "detailed_content": f"Detailed study material for {subject} Chapter {chapter_number}...",
                "examples": ["Example 1", "Example 2"],
                "summary": f"Summary of {subject} Chapter {chapter_number} concepts."
            }
        
        try:
            prompt = f"""
            Create comprehensive study material for {subject} Chapter {chapter_number} for a {student_level} student.
            
            Include:
            1. Chapter title and overview
            2. Key concepts (3-5 main points)
            3. Detailed explanations
            4. Practical examples
            5. Summary
            
            Format as structured content suitable for offline study.
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            
            return {
                "title": f"{subject} - Chapter {chapter_number}",
                "overview": f"Chapter {chapter_number} of {subject} covering essential concepts.",
                "key_concepts": [
                    f"Key concept 1 in {subject}",
                    f"Key concept 2 in {subject}",
                    f"Key concept 3 in {subject}"
                ],
                "detailed_content": content,
                "examples": [
                    f"Example 1: Practical application in {subject}",
                    f"Example 2: Real-world scenario in {subject}"
                ],
                "summary": f"Chapter {chapter_number} summary: Essential {subject} concepts for {student_level} level."
            }
            
        except Exception as e:
            print(f"⚠️ Error generating fallback content: {e}")
            return {
                "title": f"{subject} - Chapter {chapter_number}",
                "overview": f"Chapter {chapter_number} of {subject}",
                "key_concepts": ["Concept 1", "Concept 2", "Concept 3"],
                "detailed_content": f"Study material for {subject} Chapter {chapter_number}",
                "examples": ["Example 1", "Example 2"],
                "summary": f"Summary of {subject} Chapter {chapter_number}"
            }
    
    async def _generate_enhanced_quiz(self, subject: str, chapter_number: int, study_material: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enhanced quiz based on study material"""
        
        if not self.client:
            return {
                "quiz_title": f"{subject} Chapter {chapter_number} Assessment",
                "questions": [
                    {
                        "id": 1,
                        "question": f"What is the main concept in {subject} Chapter {chapter_number}?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_answer": 0,
                        "explanation": "This is the correct answer because..."
                    }
                ],
                "total_questions": 1,
                "passing_score": 70
            }
        
        try:
            prompt = f"""
            Create a 5-question multiple choice quiz for {subject} Chapter {chapter_number}.
            
            Based on this study material:
            Title: {study_material.get('title', 'N/A')}
            Key Concepts: {', '.join(study_material.get('key_concepts', []))}
            Content: {study_material.get('detailed_content', '')[:500]}...
            
            Create questions that test understanding of the key concepts.
            Each question should have 4 options (A, B, C, D) with one correct answer.
            Include explanations for correct answers.
            
            Format as JSON with this structure:
            {{
                "quiz_title": "Quiz Title",
                "questions": [
                    {{
                        "id": 1,
                        "question": "Question text?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_answer": 0,
                        "explanation": "Explanation of correct answer"
                    }}
                ],
                "total_questions": 5,
                "passing_score": 70
            }}
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            
            # Try to parse JSON response
            try:
                quiz_data = json.loads(content)
                return quiz_data
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "quiz_title": f"{subject} Chapter {chapter_number} Assessment",
                    "questions": [
                        {
                            "id": 1,
                            "question": f"What is the main concept in {subject} Chapter {chapter_number}?",
                            "options": ["Option A", "Option B", "Option C", "Option D"],
                            "correct_answer": 0,
                            "explanation": "This is the correct answer because..."
                        }
                    ],
                    "total_questions": 1,
                    "passing_score": 70
                }
            
        except Exception as e:
            print(f"⚠️ Error generating quiz: {e}")
            return {
                "quiz_title": f"{subject} Chapter {chapter_number} Assessment",
                "questions": [
                    {
                        "id": 1,
                        "question": f"What is the main concept in {subject} Chapter {chapter_number}?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_answer": 0,
                        "explanation": "This is the correct answer because..."
                    }
                ],
                "total_questions": 1,
                "passing_score": 70
            }
    
    def save_learning_pack(self, learning_pack: Dict[str, Any], file_path: str = None) -> str:
        """Save learning pack to JSON file"""
        
        if not file_path:
            # Save to the main learning_pack.json file
            file_path = "/Users/mac/tutor_agent/backend/learning_pack.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(learning_pack, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Enhanced learning pack saved to: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"❌ Error saving learning pack: {e}")
            return None

# Example usage
async def main():
    """Example of generating an enhanced learning pack"""
    generator = EnhancedLearningPackGenerator()
    
    # Generate enhanced learning pack for Math Chapter 1
    learning_pack = await generator.generate_enhanced_learning_pack(
        subject="Mathematics",
        chapter_number=1,
        student_level="beginner"
    )
    
    # Save the learning pack
    file_path = generator.save_learning_pack(learning_pack)
    
    if file_path:
        print(f"📚 Enhanced learning pack generated successfully!")
        print(f"📁 File: {file_path}")
        print(f"📖 Subject: {learning_pack['pack_info']['subject']}")
        print(f"📝 Chapter: {learning_pack['pack_info']['chapter_number']}")
        print(f"📚 Source: {learning_pack['pack_info']['source']}")
        print(f"❓ Quiz Questions: {learning_pack['assessment']['total_questions']}")

if __name__ == "__main__":
    asyncio.run(main())
