#!/usr/bin/env python3
"""
Offline Learning Agent
Handles offline study sessions using pre-generated learning packs.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class OfflineLearningAgent:
    """Handles offline learning sessions using learning packs"""
    
    def __init__(self, learning_pack_path: str = None):
        self.learning_pack = None
        self.current_question = 0
        self.quiz_answers = []
        self.study_progress = 0
        
        if learning_pack_path:
            self.load_learning_pack(learning_pack_path)
    
    def load_learning_pack(self, file_path: str) -> bool:
        """Load learning pack from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.learning_pack = json.load(f)
            
            print(f"✅ Learning pack loaded: {self.learning_pack['pack_info']['title']}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading learning pack: {e}")
            return False
    
    def get_pack_info(self) -> Dict[str, Any]:
        """Get basic information about the loaded learning pack"""
        if not self.learning_pack:
            return {"error": "No learning pack loaded"}
        
        return {
            "title": self.learning_pack["pack_info"]["title"],
            "subject": self.learning_pack["pack_info"]["subject"],
            "chapter": self.learning_pack["pack_info"]["chapter_number"],
            "created": self.learning_pack["pack_info"]["created_date"],
            "expires": self.learning_pack["pack_info"]["expires_date"],
            "status": self.learning_pack["pack_info"]["status"]
        }
    
    def start_study_session(self) -> str:
        """Start a new study session"""
        if not self.learning_pack:
            return "❌ No learning pack loaded. Please load a learning pack first."
        
        pack_info = self.learning_pack["pack_info"]
        study_material = self.learning_pack["study_material"]
        
        welcome_message = f"""
📚 Welcome to your offline study session!

📖 Subject: {pack_info['subject']}
📝 Chapter: {pack_info['chapter_number']}
🎯 Title: {study_material['title']}

📋 What you'll learn today:
{chr(10).join([f"• {concept}" for concept in study_material['key_concepts']])}

💡 Commands available:
• 'study' - Read the study material
• 'quiz' - Take the assessment quiz
• 'summary' - Get chapter summary
• 'progress' - Check your progress
• 'help' - Show available commands

Ready to start learning! Type 'study' to begin.
        """
        
        return welcome_message.strip()
    
    def get_study_material(self) -> str:
        """Get the study material content"""
        if not self.learning_pack:
            return "❌ No learning pack loaded."
        
        study_material = self.learning_pack["study_material"]
        
        content = f"""
📖 {study_material['title']}

📋 Overview:
{study_material['overview']}

🎯 Key Concepts:
{chr(10).join([f"• {concept}" for concept in study_material['key_concepts']])}

📚 Detailed Content:
{study_material['detailed_content']}

💡 Examples:
{chr(10).join([f"• {example}" for example in study_material['examples']])}

📝 Summary:
{study_material['summary']}

✅ Study material completed! Type 'quiz' to take the assessment.
        """
        
        self.study_progress = 100
        return content.strip()
    
    def start_quiz(self) -> str:
        """Start the assessment quiz"""
        if not self.learning_pack:
            return "❌ No learning pack loaded."
        
        assessment = self.learning_pack["assessment"]
        self.current_question = 0
        self.quiz_answers = []
        
        return f"""
🧠 Assessment Quiz: {assessment['quiz_title']}

📊 Quiz Information:
• Total Questions: {assessment['total_questions']}
• Passing Score: {assessment['passing_score']}%
• Time: Take your time, no rush!

Type 'next' to start the first question.
        """.strip()
    
    def get_next_question(self) -> str:
        """Get the next quiz question"""
        if not self.learning_pack:
            return "❌ No learning pack loaded."
        
        assessment = self.learning_pack["assessment"]
        
        if self.current_question >= assessment["total_questions"]:
            return self.get_quiz_results()
        
        question = assessment["questions"][self.current_question]
        
        question_text = f"""
❓ Question {self.current_question + 1} of {assessment['total_questions']}

{question['question']}

A) {question['options'][0]}
B) {question['options'][1]}
C) {question['options'][2]}
D) {question['options'][3]}

Type your answer: A, B, C, or D
        """
        
        return question_text.strip()
    
    def submit_answer(self, answer: str) -> str:
        """Submit an answer to the current question"""
        if not self.learning_pack:
            return "❌ No learning pack loaded."
        
        assessment = self.learning_pack["assessment"]
        
        if self.current_question >= assessment["total_questions"]:
            return "❌ No more questions. Type 'results' to see your score."
        
        # Convert answer to index
        answer_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
        answer_index = answer_map.get(answer.upper(), -1)
        
        if answer_index == -1:
            return "❌ Invalid answer. Please type A, B, C, or D."
        
        question = assessment["questions"][self.current_question]
        is_correct = answer_index == question["correct_answer"]
        
        # Store the answer
        self.quiz_answers.append({
            "question_id": question["id"],
            "user_answer": answer_index,
            "correct_answer": question["correct_answer"],
            "is_correct": is_correct
        })
        
        # Move to next question
        self.current_question += 1
        
        if is_correct:
            response = "✅ Correct! Well done!"
        else:
            correct_option = chr(65 + question["correct_answer"])  # A, B, C, or D
            response = f"❌ Incorrect. The correct answer is {correct_option}."
        
        response += f"\n💡 Explanation: {question['explanation']}"
        
        if self.current_question < assessment["total_questions"]:
            response += "\n\nType 'next' for the next question."
        else:
            response += "\n\n🎉 Quiz completed! Type 'results' to see your final score."
        
        return response
    
    def get_quiz_results(self) -> str:
        """Get the final quiz results"""
        if not self.learning_pack:
            return "❌ No learning pack loaded."
        
        if not self.quiz_answers:
            return "❌ No quiz answers found. Start a quiz first."
        
        assessment = self.learning_pack["assessment"]
        total_questions = len(self.quiz_answers)
        correct_answers = sum(1 for answer in self.quiz_answers if answer["is_correct"])
        score_percentage = (correct_answers / total_questions) * 100
        passed = score_percentage >= assessment["passing_score"]
        
        # Update progress in learning pack
        self.learning_pack["progress"]["completed"] = True
        self.learning_pack["progress"]["score"] = score_percentage
        self.learning_pack["progress"]["last_accessed"] = datetime.now().isoformat()
        
        results = f"""
🎉 Quiz Results

📊 Your Score: {correct_answers}/{total_questions} ({score_percentage:.1f}%)
🎯 Passing Score: {assessment['passing_score']}%
{'✅ Congratulations! You passed!' if passed else '❌ You need to study more. Try again!'}

📋 Question Breakdown:
        """
        
        for i, answer in enumerate(self.quiz_answers):
            status = "✅" if answer["is_correct"] else "❌"
            user_choice = chr(65 + answer["user_answer"])
            correct_choice = chr(65 + answer["correct_answer"])
            results += f"\n{status} Question {i+1}: You chose {user_choice}, Correct was {correct_choice}"
        
        if passed:
            results += "\n\n🎓 Great job! You've mastered this chapter!"
        else:
            results += f"\n\n📚 Don't worry! Review the material and try again. You need {assessment['passing_score']}% to pass."
        
        return results.strip()
    
    def get_summary(self) -> str:
        """Get chapter summary"""
        if not self.learning_pack:
            return "❌ No learning pack loaded."
        
        study_material = self.learning_pack["study_material"]
        
        return f"""
📝 Chapter Summary: {study_material['title']}

🎯 Key Concepts Covered:
{chr(10).join([f"• {concept}" for concept in study_material['key_concepts']])}

📚 Summary:
{study_material['summary']}

💡 Examples:
{chr(10).join([f"• {example}" for example in study_material['examples']])}

✅ You've completed this chapter! Great work!
        """.strip()
    
    def get_progress(self) -> str:
        """Get current progress"""
        if not self.learning_pack:
            return "❌ No learning pack loaded."
        
        progress = self.learning_pack["progress"]
        
        progress_text = f"""
📊 Your Progress

📖 Study Material: {'✅ Completed' if self.study_progress == 100 else f'⏳ {self.study_progress}% Complete'}
🧠 Quiz: {'✅ Completed' if progress['completed'] else '⏳ Not Started'}
📊 Quiz Score: {progress['score'] if progress['score'] is not None else 'Not taken yet'}
⏰ Last Accessed: {progress['last_accessed'] if progress['last_accessed'] else 'Never'}

💡 Commands:
• 'study' - Continue studying
• 'quiz' - Take the quiz
• 'summary' - Get summary
        """
        
        return progress_text.strip()
    
    def save_progress(self, file_path: str = None) -> bool:
        """Save progress back to learning pack file"""
        if not self.learning_pack:
            return False
        
        if not file_path:
            pack_id = self.learning_pack["pack_info"]["pack_id"]
            file_path = f"/Users/mac/tutor_agent/backend/learning_pack_{pack_id}.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.learning_pack, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Progress saved to: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving progress: {e}")
            return False
    
    def handle_command(self, user_input: str) -> str:
        """Handle user commands for offline learning"""
        command = user_input.lower().strip()
        
        if command == "help":
            return """
📚 Offline Learning Commands:

📖 Study Commands:
• 'study' - Read the study material
• 'summary' - Get chapter summary
• 'progress' - Check your progress

🧠 Quiz Commands:
• 'quiz' - Start the assessment quiz
• 'next' - Get next question (during quiz)
• 'results' - See quiz results

💡 General:
• 'info' - Show learning pack information
• 'help' - Show this help message
            """.strip()
        
        elif command == "study":
            return self.get_study_material()
        
        elif command == "quiz":
            return self.start_quiz()
        
        elif command == "next":
            return self.get_next_question()
        
        elif command == "results":
            return self.get_quiz_results()
        
        elif command == "summary":
            return self.get_summary()
        
        elif command == "progress":
            return self.get_progress()
        
        elif command == "info":
            info = self.get_pack_info()
            if "error" in info:
                return info["error"]
            
            return f"""
📚 Learning Pack Information

📖 Title: {info['title']}
📝 Subject: {info['subject']}
📊 Chapter: {info['chapter']}
📅 Created: {info['created']}
⏰ Expires: {info['expires']}
✅ Status: {info['status']}
            """.strip()
        
        elif command in ['a', 'b', 'c', 'd']:
            return self.submit_answer(command)
        
        else:
            return """
❓ I didn't understand that command.

Type 'help' to see available commands, or try:
• 'study' - Read study material
• 'quiz' - Take assessment
• 'progress' - Check progress
            """.strip()

# Example usage
def main():
    """Example of using the offline learning agent"""
    agent = OfflineLearningAgent()
    
    # Load a learning pack
    pack_path = "/Users/mac/tutor_agent/backend/learning_pack_math_ch001.json"
    
    if agent.load_learning_pack(pack_path):
        print(agent.start_study_session())
        
        # Example interaction
        print("\n" + "="*50)
        print(agent.handle_command("study"))
        print("\n" + "="*50)
        print(agent.handle_command("quiz"))
        print("\n" + "="*50)
        print(agent.handle_command("next"))

if __name__ == "__main__":
    main()
