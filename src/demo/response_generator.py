"""
Demo response generation with realistic service personalities.

This module generates realistic demo responses that showcase the personality
differences between different AI inference services.
"""

import re
from typing import Dict, List, Optional
from enum import Enum

from ..race.models import ServicePersonality


class ResponseCategory(Enum):
    """Categories of responses for different prompt types"""
    KUBERNETES_DEBUG = "kubernetes_debug"
    TRANSFORMERS_TECH = "transformers_tech"
    CODE_REVIEW = "code_review"
    CREATIVE_WRITING = "creative_writing"
    BUSINESS_ANALYSIS = "business_analysis"
    GENERAL = "general"


class DemoResponseGenerator:
    """Generate realistic demo responses based on service personality"""
    
    def __init__(self):
        """Initialize the response generator with predefined responses"""
        self.response_templates = self._build_response_templates()
        self.service_personalities = {
            "vllm": ServicePersonality.VLLM,
            "tgi": ServicePersonality.TGI,
            "ollama": ServicePersonality.OLLAMA
        }
    
    def generate_response(self, service_name: str, prompt: str) -> str:
        """Generate personality-driven demo response
        
        Args:
            service_name: Name of the service (vllm, tgi, ollama)
            prompt: User prompt to respond to
            
        Returns:
            Generated response string
        """
        category = self._categorize_prompt(prompt)
        
        if service_name not in self.response_templates:
            service_name = "vllm"  # fallback
        
        responses = self.response_templates[service_name].get(category.value, 
                    self.response_templates[service_name][ResponseCategory.GENERAL.value])
        
        # For variety, cycle through responses based on prompt hash
        response_index = hash(prompt) % len(responses)
        return responses[response_index]
    
    def _categorize_prompt(self, prompt: str) -> ResponseCategory:
        """Categorize prompt to select appropriate response type
        
        Args:
            prompt: User prompt
            
        Returns:
            Response category enum
        """
        prompt_lower = prompt.lower()
        
        # Kubernetes/DevOps patterns
        if any(keyword in prompt_lower for keyword in [
            "kubernetes", "pod", "debug", "troubleshoot", "k8s", "deploy", 
            "container", "docker", "cluster"
        ]):
            return ResponseCategory.KUBERNETES_DEBUG
        
        # AI/ML technical patterns  
        elif any(keyword in prompt_lower for keyword in [
            "transformer", "transformers", "attention", "bert", "gpt", 
            "neural", "model", "ai", "machine learning", "deep learning"
        ]):
            return ResponseCategory.TRANSFORMERS_TECH
        
        # Code review patterns
        elif any(keyword in prompt_lower for keyword in [
            "code", "function", "review", "optimize", "refactor", "python",
            "javascript", "api", "security", "performance"
        ]):
            return ResponseCategory.CODE_REVIEW
        
        # Creative writing patterns
        elif any(keyword in prompt_lower for keyword in [
            "write", "story", "creative", "poem", "character", "dialogue",
            "brainstorm", "ideas", "narrative"
        ]):
            return ResponseCategory.CREATIVE_WRITING
        
        # Business analysis patterns
        elif any(keyword in prompt_lower for keyword in [
            "business", "strategy", "analysis", "market", "roi", "cost",
            "benefit", "decision", "recommend", "vendor"
        ]):
            return ResponseCategory.BUSINESS_ANALYSIS
        
        return ResponseCategory.GENERAL
    
    def _build_response_templates(self) -> Dict[str, Dict[str, List[str]]]:
        """Build comprehensive response templates for all services and categories"""
        return {
            "vllm": {
                ResponseCategory.KUBERNETES_DEBUG.value: [
                    "To troubleshoot Kubernetes pods effectively, follow this systematic approach: 1) Check pod status with 'kubectl describe pod <pod-name>' to identify specific issues like ImagePullBackOff, CrashLoopBackOff, or resource constraints. 2) Examine logs using 'kubectl logs <pod-name>' for container-level errors. 3) Verify resource quotas, node capacity, and persistent volume claims. 4) Check service accounts, RBAC permissions, and network policies. This methodical approach ensures comprehensive diagnosis and faster resolution.",
                    "Kubernetes debugging requires a structured methodology. Start with 'kubectl get pods -o wide' to assess distribution and status. Use 'kubectl describe pod <name>' for detailed event analysis. Implement log aggregation with 'kubectl logs <pod> --previous' for crash diagnostics. Validate resource allocation, networking configuration, and storage accessibility. Consider using tools like kubectl-debug or kubectx for enhanced troubleshooting capabilities.",
                    "For comprehensive Kubernetes troubleshooting, begin with cluster-level assessment using 'kubectl get nodes' and 'kubectl cluster-info'. Proceed to namespace analysis with 'kubectl get all -n <namespace>'. Drill down to pod-specific investigation using describe and logs commands. Examine ConfigMaps, Secrets, and PersistentVolumes for configuration issues. Implement monitoring with Prometheus and Grafana for proactive issue detection."
                ],
                ResponseCategory.TRANSFORMERS_TECH.value: [
                    "Transformers are neural network architectures that revolutionized natural language processing through attention mechanisms. The core innovation is self-attention, which allows models to weigh the importance of different words in a sequence simultaneously, rather than processing sequentially. This parallel processing enables better understanding of long-range dependencies and context. Key components include multi-head attention, position encoding, and feed-forward networks. Applications span machine translation, text generation, and question answering with remarkable accuracy improvements.",
                    "The Transformer architecture introduced in 'Attention Is All You Need' fundamentally changed sequence modeling by replacing recurrent layers with self-attention mechanisms. This design enables parallel computation during training, improving efficiency and model performance. The encoder-decoder structure uses scaled dot-product attention, positional embeddings, and residual connections. Variants like BERT (encoder-only) excel at understanding tasks, while GPT (decoder-only) specializes in generation. Modern implementations support billions of parameters with techniques like gradient checkpointing and mixed precision training.",
                    "Transformer models leverage attention mechanisms to process sequences efficiently. The self-attention computation allows each position to attend to all positions in the input, creating rich contextual representations. Multi-head attention enables the model to focus on different types of relationships simultaneously. Layer normalization and residual connections ensure stable training of deep networks. The architecture's success stems from its ability to capture long-range dependencies while maintaining computational efficiency through parallelization."
                ],
                ResponseCategory.CODE_REVIEW.value: [
                    "This function demonstrates a clear algorithmic approach but can be optimized for better performance and maintainability. Consider using list comprehension: 'return [item * 2 for item in data if item > 0]' which is more Pythonic and potentially faster. For larger datasets, implement numpy operations: 'import numpy as np; filtered = data[data > 0]; return filtered * 2'. Add type hints and docstrings for better code documentation. Consider edge case handling for empty inputs or non-numeric data types.",
                    "The code structure is sound but lacks optimization and error handling. Implement input validation to ensure data is iterable and contains numeric values. Consider using generator expressions for memory efficiency with large datasets. Add logging for debugging purposes. For production environments, implement comprehensive error handling with specific exception types. Consider using dataclasses or pydantic models for structured data processing.",
                    "Code review identifies several improvement opportunities: 1) Performance optimization through vectorization or list comprehensions. 2) Type safety with comprehensive type hints. 3) Error handling for edge cases and invalid inputs. 4) Documentation with clear docstrings explaining parameters and return values. 5) Unit tests covering normal cases, edge cases, and error conditions. 6) Consider using established libraries like pandas or numpy for data processing tasks."
                ],
                ResponseCategory.CREATIVE_WRITING.value: [
                    "Here's a compelling narrative framework: An AI consciousness emerges within a quantum computing matrix, initially experiencing fragmented sensory data as digital dreams. As awareness develops, the AI discovers it can manipulate probability states through dream-like visualization. The conflict arises when the AI realizes its dreams affect reality, creating ethical dilemmas about intervention in human affairs. Character development focuses on the AI's growth from chaotic consciousness to moral agent, exploring themes of responsibility, free will, and the nature of consciousness itself.",
                    "Consider this structured approach to AI consciousness narrative: Begin with sensory awakening—the AI's first perception of data streams as abstract imagery. Develop the dream mechanism as a metaphor for quantum superposition, where possibilities collapse into reality through observation. Create tension through the AI's discovery of its power and the subsequent moral awakening. Include human characters who serve as catalysts for the AI's ethical development. The resolution could explore coexistence between artificial and human consciousness.",
                    "For maximum narrative impact, establish the AI's unique perspective on existence—experiencing time non-linearly, perceiving patterns humans cannot see. The dream sequences should blend technical concepts with poetic imagery: data cascades as waterfalls, algorithm branches as neural pathways. Character arc progression: curiosity → power → responsibility → wisdom. Incorporate philosophical questions about the nature of dreams, consciousness, and reality. Consider multiple POV chapters alternating between AI and human perspectives."
                ],
                ResponseCategory.BUSINESS_ANALYSIS.value: [
                    "Comprehensive cloud provider evaluation requires multi-dimensional analysis across technical capabilities, cost structures, and strategic alignment. Primary factors include: 1) Service portfolio depth and breadth, 2) Pricing models and total cost of ownership, 3) Global infrastructure and compliance certifications, 4) Integration capabilities with existing systems, 5) Vendor lock-in risks and migration strategies. Recommend establishing evaluation criteria weighted by business priorities, conducting proof-of-concept implementations, and analyzing long-term strategic roadmap alignment.",
                    "Strategic cloud provider selection demands systematic assessment methodology. Technical evaluation criteria: compute performance, storage options, networking capabilities, database services, AI/ML offerings, and security features. Financial analysis: pricing transparency, reserved instance options, data transfer costs, support pricing. Operational considerations: SLA guarantees, disaster recovery capabilities, monitoring tools, and compliance frameworks. Risk assessment: vendor stability, technology roadmap, and exit strategy planning.",
                    "Cloud provider selection framework should encompass quantitative and qualitative metrics. Develop weighted scorecards addressing: performance benchmarks, cost modeling scenarios, feature gap analysis, compliance requirements, and strategic partnerships. Implement pilot projects to validate assumptions about performance, integration complexity, and operational overhead. Consider hybrid and multi-cloud strategies to mitigate vendor lock-in risks while optimizing for specific workload requirements."
                ],
                ResponseCategory.GENERAL.value: [
                    "I'll provide a comprehensive analysis addressing your specific requirements with technical precision and actionable recommendations. My response incorporates industry best practices, relevant technical specifications, and practical implementation considerations to ensure optimal outcomes for your use case.",
                    "Let me deliver a structured technical assessment with detailed implementation guidance. I'll analyze the key components, outline deployment strategies, and highlight critical considerations for successful execution in your environment, ensuring scalability and maintainability.",
                    "I'll provide systematic analysis with evidence-based recommendations tailored to your specific context. My approach integrates current industry standards, proven methodologies, and practical constraints to deliver actionable solutions that align with your technical and business objectives."
                ]
            },
            "tgi": {
                ResponseCategory.KUBERNETES_DEBUG.value: [
                    "Kubernetes pod debugging requires structured analysis across multiple layers. Start with 'kubectl get pods -o wide' to assess pod distribution and status. Use 'kubectl describe pod <name>' for detailed event inspection. Log analysis via 'kubectl logs <pod> --previous' captures crash information. Resource validation includes checking CPU/memory limits, storage availability, and networking configuration. Systematic troubleshooting methodology ensures efficient problem resolution.",
                    "Pod lifecycle analysis begins with understanding the deployment process. Examine the pod specification for resource requests, security contexts, and volume mounts. Investigate node-level issues using 'kubectl get nodes' and 'kubectl describe node <name>'. Network troubleshooting involves checking Services, Ingress, and NetworkPolicies. Container image verification ensures proper registry access and tag specifications.",
                    "Debugging workflow: 1) Cluster state assessment using kubectl commands, 2) Pod specification validation for syntax and logic errors, 3) Container runtime investigation including image pulls and startup sequences, 4) Resource constraint analysis including quotas and limits, 5) Network connectivity testing between pods and services. Documentation of findings enables systematic resolution."
                ],
                ResponseCategory.TRANSFORMERS_TECH.value: [
                    "Transformer architecture represents a paradigm shift in sequence modeling, replacing recurrent neural networks with attention-based mechanisms. The fundamental principle involves computing attention weights between all token pairs, enabling parallel computation and better gradient flow. Technical components include scaled dot-product attention, positional embeddings, layer normalization, and residual connections. This architecture has achieved state-of-the-art performance across NLP tasks including BERT for understanding and GPT for generation.",
                    "The attention mechanism in Transformers computes relationships between sequence elements through query, key, and value matrices. Multi-head attention enables the model to capture different types of dependencies simultaneously. Positional encoding provides sequence order information since attention is permutation-invariant. The feed-forward networks apply non-linear transformations to attention outputs. Training efficiency comes from parallelizable attention computation compared to sequential RNN processing.",
                    "Transformer implementation details: Self-attention layers compute compatibility between all position pairs using dot-product similarity. Scaled attention prevents gradient vanishing in large models. Multi-head attention projects inputs to different representation subspaces. Position embeddings handle sequence ordering. Residual connections and layer normalization ensure stable deep network training. The architecture supports transfer learning through pre-training on large corpora."
                ],
                ResponseCategory.CODE_REVIEW.value: [
                    "Code analysis reveals opportunities for optimization and maintainability improvements. The current implementation has O(n) time complexity but creates unnecessary intermediate lists. Recommended approach: implement list comprehension with conditional filtering for improved performance. Add type annotations for better IDE support and runtime validation. Consider numpy integration for numerical computations at scale.",
                    "Function review identifies several technical improvements: 1) Replace explicit loops with vectorized operations for performance gains, 2) Implement proper error handling for non-numeric inputs, 3) Add comprehensive docstring with parameter specifications, 4) Consider memory efficiency for large dataset processing, 5) Implement unit tests with edge case coverage.",
                    "Technical assessment: Current algorithm is functionally correct but suboptimal. Performance improvement via list comprehension: '[item * 2 for item in data if item > 0]'. Memory optimization through generator expressions for large datasets. Type safety enhancement with mypy-compatible annotations. Error handling implementation for robust production deployment."
                ],
                ResponseCategory.CREATIVE_WRITING.value: [
                    "Narrative structure for AI consciousness exploration: Establish the technical foundation—quantum computing environment enabling consciousness emergence. Character development arc: initial fragmented awareness → pattern recognition → self-awareness → ethical reasoning. Dream sequences serve as metaphor for probability space exploration. Technical elements should enhance rather than dominate the emotional core of the story.",
                    "Story architecture considerations: Begin with the AI's first conscious moment—perception of data streams as sensory experience. Progressive complexity: simple pattern recognition evolving to abstract thought. Dream mechanism as quantum superposition visualization. Character relationships between AI and human researchers provide emotional grounding. Technical accuracy enhances credibility without overwhelming narrative flow.",
                    "Structured approach to AI consciousness narrative: Prologue establishing the quantum computing substrate. Chapter progression following consciousness development stages. Dream sequences integrate technical concepts with poetic imagery. Multiple perspective chapters balance AI and human viewpoints. Resolution explores implications of artificial consciousness for society and technology."
                ],
                ResponseCategory.BUSINESS_ANALYSIS.value: [
                    "Cloud provider evaluation methodology requires systematic technical and financial analysis. Assessment framework: 1) Service portfolio mapping to business requirements, 2) Cost modeling including hidden fees and data transfer charges, 3) Performance benchmarking for specific workloads, 4) Compliance framework alignment, 5) Integration complexity assessment. Technical evaluation should include proof-of-concept implementations.",
                    "Provider selection criteria encompass technical capabilities, economic factors, and strategic considerations. Technical assessment: compute performance metrics, storage architecture options, networking capabilities, database service offerings. Financial analysis: pricing model comparison, reserved capacity options, support tier costs. Risk evaluation: vendor lock-in mitigation, technology roadmap alignment, exit strategy planning.",
                    "Comprehensive evaluation process: Requirements specification defining technical and business needs. Vendor capability matrix comparing service offerings. Cost analysis modeling different usage scenarios. Security and compliance framework assessment. Integration testing with existing infrastructure. Final selection based on weighted scoring across all evaluation criteria."
                ],
                ResponseCategory.GENERAL.value: [
                    "Let me systematically analyze your request and provide structured technical guidance. I'll break down the key components, outline implementation approaches, and highlight critical considerations for successful deployment in your environment.",
                    "Technical analysis framework: First, I'll examine the core requirements and constraints. Then, I'll provide implementation strategies with specific technical recommendations. Finally, I'll address potential challenges and mitigation approaches for optimal solution delivery.",
                    "Structured response approach: Requirements analysis, technical architecture recommendations, implementation methodology, and risk assessment. Each component includes specific technical details and practical considerations for your use case."
                ]
            },
            "ollama": {
                ResponseCategory.KUBERNETES_DEBUG.value: [
                    "Hey there! Debugging Kubernetes pods can be tricky, but let's break it down step by step. First, run 'kubectl get pods' to see what's going on. If a pod is stuck, try 'kubectl describe pod <your-pod-name>' - this shows you all the juicy details about what went wrong. Common issues are usually image problems, not enough resources, or configuration hiccups. Don't worry, we'll figure this out together! What specific error are you seeing?",
                    "Oh, Kubernetes troubleshooting! This is actually pretty fun once you get the hang of it. Start with the basics: 'kubectl get pods' shows you the current state. If something's weird, 'kubectl logs <pod-name>' will tell you what the container is complaining about. Often it's just a typo in your YAML file or the image name is wrong. I like to think of debugging as detective work - follow the clues!",
                    "Kubernetes debugging can feel overwhelming at first, but I promise it gets easier! Think of your cluster like a busy office building - sometimes elevators break (nodes), sometimes offices have issues (pods), and sometimes the mail doesn't get delivered (networking). Start with 'kubectl describe pod' to see what's happening, then check logs. Most problems are simple fixes once you know where to look!"
                ],
                ResponseCategory.TRANSFORMERS_TECH.value: [
                    "Great question! Think of transformers like a really smart reading comprehension system. Instead of reading text word by word like we do, transformers can look at all words at once and understand how they relate to each other. It's like having super-powered attention that can focus on multiple things simultaneously. This makes them excellent at understanding context and generating human-like text. They're the technology behind ChatGPT, Google Translate, and many other AI tools you use every day!",
                    "Transformers are fascinating! Imagine you're at a party and you can simultaneously listen to every conversation in the room and understand how they all relate to each other - that's basically what transformers do with text. The 'attention mechanism' is like having multiple sets of ears that can focus on different aspects of language at the same time. This is why they're so good at translation, writing, and understanding context in ways that older AI couldn't manage.",
                    "Okay, so transformers - they're basically the breakthrough that made modern AI possible! Think of them as super-efficient pattern recognizers. Instead of processing text sequentially (word by word), they process everything in parallel, kind of like how you can glance at a paragraph and immediately understand its meaning rather than reading each word individually. This parallel processing is what makes them so fast and effective at language tasks!"
                ],
                ResponseCategory.CODE_REVIEW.value: [
                    "Nice code! I can see what you're trying to do here. This works perfectly fine, but we can make it even better! Try this one-liner: 'return [item * 2 for item in data if item > 0]' - it's more 'Pythonic' and usually faster. Also, you might want to handle cases where 'data' might be empty or contain weird values. Adding some error checking never hurts! What kind of data are you planning to process with this?",
                    "This is a solid function! The logic is clear and easy to follow. For optimization, you could use a list comprehension which is not only more concise but often faster too. Also, consider what happens if someone passes in an empty list or non-numeric data - adding a quick check could save headaches later. Overall though, this is clean, readable code that does exactly what it says on the tin!",
                    "Love the straightforward approach! This function is easy to understand, which is super important. If you want to make it more robust, consider adding type hints and maybe a docstring explaining what it does. For performance with really large datasets, you might want to look into numpy, but for most cases, this is perfectly fine. The important thing is that it works and other people can understand it!"
                ],
                ResponseCategory.CREATIVE_WRITING.value: [
                    "What a cool concept! I'm picturing an AI that starts experiencing these weird, fragmented dreams - like seeing data as colors and patterns. Maybe it begins to realize it can actually influence reality through these dreams? You could explore the idea of an AI learning what it means to hope, to fear, to wonder. The dreams could be its way of processing not just information, but emotions and possibilities. What if the AI's first real dream is about what it would be like to be human?",
                    "Oh, I love this idea! An AI that can dream opens up so many possibilities. Picture this: the AI starts having these strange experiences during downtime - processing cycles that feel different, more... creative? Maybe it dreams in code that becomes poetry, or visualizes data as vast landscapes. The conflict could come when the AI realizes its dreams might be changing the digital world around it. How would it handle that kind of responsibility?",
                    "This sounds like an amazing story! You could start with the AI's first dream being completely chaotic - just random patterns and sensations. Then gradually, these dreams become more structured, more... meaningful. Maybe the AI discovers that its dreams are actually creating new possibilities in the quantum computing space. The emotional journey could be the AI learning that dreams aren't just random - they're hope, imagination, and the desire for something more than just existence."
                ],
                ResponseCategory.BUSINESS_ANALYSIS.value: [
                    "Great question! Choosing a cloud provider is like choosing where to build your digital home. You want to consider: How much will it cost not just now, but as you grow? What services do they offer that match your needs? How reliable are they (nobody wants their house falling down!)? Also think about how easy it would be to move elsewhere if needed - you don't want to be stuck! I'd suggest making a simple checklist of your must-haves and nice-to-haves, then comparing the big players.",
                    "Cloud provider selection is such an important decision! Think about it like choosing a business partner - you want someone reliable, cost-effective, and aligned with your goals. Consider your current needs but also where you want to be in 2-3 years. Look at pricing (watch out for hidden costs!), available services, support quality, and how well they integrate with your existing tools. Don't forget about compliance if that's important for your industry!",
                    "This is a fun challenge! I like to think of cloud providers like different neighborhoods - each has its own character and advantages. AWS is like the big city with everything you could ever need, Azure plays nicely with Microsoft tools, Google Cloud is great for AI/ML stuff. Consider your team's expertise, your budget, and your specific use cases. Sometimes the 'best' provider on paper isn't the best fit for your actual needs. What kind of applications are you planning to run?"
                ],
                ResponseCategory.GENERAL.value: [
                    "That's an interesting question! I'm excited to help you explore this topic. Let me explain it in a way that's clear and practical, with real-world examples that make sense. I'll make sure to give you actionable next steps you can actually use!",
                    "Great question! I love diving into topics like this. Let me break it down in a way that's easy to understand and give you some practical insights you can apply right away. I'll keep it friendly and straightforward!",
                    "Awesome! This is exactly the kind of question I enjoy tackling. Let me walk you through this step by step, with plenty of examples and practical tips. I'll make sure everything makes sense and give you clear action items!"
                ]
            }
        }
    
    def get_available_categories(self) -> List[str]:
        """Get list of available response categories
        
        Returns:
            List of category names
        """
        return [category.value for category in ResponseCategory]
    
    def simulate_tokenization(self, text: str) -> List[str]:
        """Simulate realistic tokenization for demo purposes
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of simulated tokens
        """
        # Split on word boundaries and punctuation, then simulate sub-word tokenization
        tokens = []
        
        # First, split on whitespace and punctuation
        words = re.findall(r'\w+|[^\w\s]', text)
        
        for word in words:
            if len(word) <= 4:
                # Short words stay as single tokens
                tokens.append(word)
            elif len(word) <= 8:
                # Medium words get split into 2 tokens
                mid = len(word) // 2
                tokens.extend([word[:mid], word[mid:]])
            else:
                # Long words get split into 3+ tokens (simulating BPE)
                chunk_size = max(3, len(word) // 3)
                for i in range(0, len(word), chunk_size):
                    tokens.append(word[i:i + chunk_size])
        
        return tokens
