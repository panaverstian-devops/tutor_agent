#!/usr/bin/env python3
"""
Learning Pack Generator
Generates daily learning packs with study material and assessments for offline use.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import asyncio
from agents import AsyncOpenAI, OpenAIChatCompletionsModel

class LearningPackGenerator:
    """Generates learning packs for offline study sessions"""
    
    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        self.model = None
        
        if self.openai_api_key:
            try:
                self.client = AsyncOpenAI(api_key=self.openai_api_key)
                self.model = OpenAIChatCompletionsModel(
                    model="gpt-3.5-turbo",
                    openai_client=self.client
                )
            except Exception as e:
                print(f"⚠️ OpenAI connection failed: {e}")
    
    async def generate_daily_learning_pack(self, subject: str, chapter_number: int, student_level: str = "beginner") -> Dict[str, Any]:
        """Generate a complete learning pack for one day"""
        
        print(f"📚 Generating learning pack for {subject} - Chapter {chapter_number}")
        
        # Generate study material
        study_material = await self._generate_study_material(subject, chapter_number, student_level)
        
        # Generate assessment quiz
        quiz = await self._generate_quiz(subject, chapter_number, study_material)
        
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
                "status": "ready"
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
    
    async def _generate_study_material(self, subject: str, chapter_number: int, student_level: str) -> Dict[str, Any]:
        """Generate comprehensive study material for the chapter"""
        
        if not self.client:
            # Fallback content if no OpenAI
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
            
            # Parse and structure the content
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
            print(f"⚠️ Error generating study material: {e}")
            return {
                "title": f"{subject} - Chapter {chapter_number}",
                "overview": f"Chapter {chapter_number} of {subject}",
                "key_concepts": ["Concept 1", "Concept 2", "Concept 3"],
                "detailed_content": f"Study material for {subject} Chapter {chapter_number}",
                "examples": ["Example 1", "Example 2"],
                "summary": f"Summary of {subject} Chapter {chapter_number}"
            }
    
    async def _generate_quiz(self, subject: str, chapter_number: int, study_material: Dict[str, Any]) -> Dict[str, Any]:
        """Generate assessment quiz for the chapter"""
        
        if not self.client:
            # Fallback quiz if no OpenAI
            return {
                "quiz_title": f"{subject} Chapter {chapter_number} Assessment",
                "questions": [
                    {
                        "id": 1,
                        "question": f"What is the main concept in {subject} Chapter {chapter_number}?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_answer": 0,
                        "explanation": "This is the correct answer because..."
                    },
                    {
                        "id": 2,
                        "question": f"Which example best illustrates {subject} concepts?",
                        "options": ["Example 1", "Example 2", "Example 3", "Example 4"],
                        "correct_answer": 1,
                        "explanation": "This example best demonstrates the concept..."
                    }
                ],
                "total_questions": 2,
                "passing_score": 70
            }
        
        try:
            prompt = f"""
            Create a 5-question multiple choice quiz for {subject} Chapter {chapter_number}.
            
            Based on this study material:
            Title: {study_material.get('title', 'N/A')}
            Key Concepts: {', '.join(study_material.get('key_concepts', []))}
            
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
            
            print(f"✅ Learning pack saved to: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"❌ Error saving learning pack: {e}")
            return None
    
    def load_learning_pack(self, file_path: str) -> Dict[str, Any]:
        """Load learning pack from JSON file"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                learning_pack = json.load(f)
            
            print(f"✅ Learning pack loaded from: {file_path}")
            return learning_pack
            
        except Exception as e:
            print(f"❌ Error loading learning pack: {e}")
            return None

# Example usage
async def main():
    """Example of generating a learning pack"""
    generator = LearningPackGenerator()
    
    # Generate learning pack for Math Chapter 1
    learning_pack = await generator.generate_daily_learning_pack(
        subject="Mathematics",
        chapter_number=1,
        student_level="beginner"
    )
    
    # Save the learning pack
    file_path = generator.save_learning_pack(learning_pack)
    
    if file_path:
        print(f"📚 Learning pack generated successfully!")
        print(f"📁 File: {file_path}")
        print(f"📖 Subject: {learning_pack['pack_info']['subject']}")
        print(f"📝 Chapter: {learning_pack['pack_info']['chapter_number']}")
        print(f"❓ Quiz Questions: {learning_pack['assessment']['total_questions']}")

if __name__ == "__main__":
    asyncio.run(main())
