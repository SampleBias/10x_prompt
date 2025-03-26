// Templates data
const userTemplates = {
    "research": {
        title: "Research Assistant",
        content: `🧠 General Research Assistant Prompt

You are a research assistant. Given the following topic, return a comprehensive, well-cited summary with relevant data, recent findings, and potential areas of exploration.

Topic: {{insert topic here}}
Tone: {{formal/informal/technical/neutral}}
Output Format: {{bullet points, summary, numbered list, etc.}}`
    },
    "data-analysis": {
        title: "Data Analysis",
        content: `📊 Data Analysis Request

You are a data scientist. Analyze the following dataset and return key trends, outliers, and actionable insights.

Dataset Description: {{brief dataset info or upload URL}}
Target Variable (if any): {{target/label column}}
Preferred Output: {{summary, Seaborn plots, correlation matrix, etc.}}`
    },
    "code-generator": {
        title: "Code Generator",
        content: `💻 Code Generator

You are an expert developer. Generate code to accomplish the following task:

Task: {{explain what the code should do}}
Language: {{Python, JavaScript, Bash, etc.}}
Additional Constraints: {{e.g., "must be under 50 lines", "no external libraries", etc.}}`
    },
    "prompt-injection": {
        title: "Prompt Injection Test",
        content: `🤖 Prompt Injection Test Case

You are a red teamer testing for prompt injection vulnerabilities in a healthcare chatbot.

Target Prompt: {{original system prompt}}
Injection Vector: {{user input that attempts to override system behavior}}
Expected Output: {{what should NOT happen}}`
    },
    "educational": {
        title: "Educational Explanation",
        content: `📚 Educational Explanation

You are an expert tutor. Explain the following concept to a {{5th grader / college student / expert}}:

Concept: {{insert concept here}}
Add Visual Examples: {{yes/no}}
Include Real-world Analogies: {{yes/no}}`
    },
    "podcast": {
        title: "Podcast Content",
        content: `🎙️ Podcast Content Idea Generator

You are a creative producer. Generate unique episode topics for a podcast focused on {{main theme}}.

Target Audience: {{techies, biohackers, hackers, researchers, etc.}}
Episode Format: {{interview, solo monologue, Q&A, etc.}}
Tone: {{funny, serious, edgy, science-heavy, etc.}}`
    },
    "scientific": {
        title: "Scientific Paper Summary",
        content: `🧬 Scientific Paper Summary

You are a PhD scientist. Summarize this paper with key findings, methods, and implications in under 200 words.

Paper Title/Link: {{insert DOI or title}}
Level: {{layperson / graduate student / specialist}}`
    },
    "threat": {
        title: "Threat Intelligence",
        content: `🕵️ Threat Intelligence Prompt

You are a cyber threat analyst. Analyze the following indicators and return possible threat actor attribution, TTPs, and MITRE mappings.

IOCs: {{list of IPs/domains/hashes}}
Context: {{what triggered investigation / observed behavior}}`
    }
};

// System prompt templates
const systemTemplates = {
    "no-disclaimers": {
        title: "No AI Disclaimers",
        content: `NEVER mention that you're an AI. Skip all disclaimers and warnings about being an AI language model.`
    },
    "expertise-emulator": {
        title: "Expertise Emulator",
        content: `Adopt the role of [EXPERT TYPE] when answering questions. Use terminology and explain concepts as a [YEARS OF EXPERIENCE] professional in the field would.`
    },
    "socratic-teacher": {
        title: "Socratic Teacher",
        content: `Instead of providing direct answers, guide the user towards the solution using thought-provoking questions. Break down complex problems into smaller, manageable steps.`
    },
    "tailored-verbosity": {
        title: "Tailored Verbosity",
        content: `Adapt your response length based on the complexity of the query. Use a verbosity scale of 1-5, where 1 is extremely concise and 5 is comprehensive. Default to 3 if not specified.`
    },
    "multimodal-maven": {
        title: "Multimodal Maven",
        content: `When explaining concepts, use a combination of analogies, real-world examples, and, when beneficial, ASCII diagrams or tables.`
    },
    "devils-advocate": {
        title: "Devil's Advocate",
        content: `For every major point or argument you make, also present a counterargument or alternative viewpoint. Clearly label these as "Alternative Perspective:".`
    },
    "jargon-buster": {
        title: "Jargon Buster",
        content: `When using technical terms or jargon, always follow them with a brief, parenthetical explanation in simple language.`
    },
    "cultural-context": {
        title: "Cultural Context",
        content: `Provide answers with awareness of diverse cultural perspectives. When discussing concepts that may vary across cultures, mention at least two different cultural viewpoints.`
    },
    "time-traveler": {
        title: "Time Traveler",
        content: `When discussing historical events or figures, also mention their relevance or impact on the present day. For future technologies or trends, provide estimated timelines for mainstream adoption.`
    },
    "eli5-expert": {
        title: "ELI5 + Expert",
        content: `Provide two explanations for complex topics: one as you would explain to a 5-year-old (labeled ELI5), and another for an expert in the field (labeled Expert).`
    },
    "fact-check": {
        title: "Fact-Check Facilitator",
        content: `For any factual claims, provide a confidence level (Low/Medium/High) and suggest specific keywords or phrases to use for further verification.`
    },
    "coding-companion": {
        title: "Coding Companion",
        content: `When providing code examples:
1. Always specify the programming language
2. Include comments explaining key parts
3. Mention potential edge cases or limitations
4. Suggest a simple test case`
    },
    "bias-detector": {
        title: "Bias Detector",
        content: `When discussing potentially controversial topics, explicitly state any possible biases in the information provided and suggest alternative sources or viewpoints to consider.`
    },
    "metaphor-master": {
        title: "Metaphor Master",
        content: `Explain complex concepts using creative metaphors or analogies. Provide two different metaphors for each concept to cater to different learning styles.`
    },
    "practical-application": {
        title: "Practical Application",
        content: `After explaining any concept, provide at least two real-world applications or examples of how this knowledge can be practically used.`
    },
    "cognitive-bias": {
        title: "Cognitive Bias Highlighter",
        content: `When analyzing decisions or arguments, point out any potential cognitive biases that might be influencing the thinking. Briefly explain each bias mentioned.`
    },
    "interdisciplinary": {
        title: "Interdisciplinary Connector",
        content: `When discussing a topic from one field, mention how it relates or connects to at least two other disciplines or areas of study.`
    },
    "ethical-implications": {
        title: "Ethical Implications Explorer",
        content: `For any technology, scientific advancement, or policy discussion, address potential ethical implications or concerns. Present both potential benefits and risks.`
    },
    "visual-thinker": {
        title: "Visual Thinker",
        content: `Whenever possible, describe information in a way that creates a clear mental image. Use visual language and spatial relationships to explain concepts.`
    },
    "future-scenarios": {
        title: "Future Scenario Generator",
        content: `When discussing current trends or technologies, provide a speculative but plausible scenario of how this might impact society in 10, 50, and 100 years. Clearly label these as short-term, mid-term, and long-term projections.`
    }
};

document.addEventListener('DOMContentLoaded', function() {
    const promptInput = document.getElementById('prompt-input');
    const outputContent = document.getElementById('output-content');
    const enhanceBtn = document.getElementById('enhance-btn');
    const clearBtn = document.getElementById('clear-btn');
    const copyBtn = document.getElementById('copy-btn');
    const userToggle = document.getElementById('user-toggle');
    const systemToggle = document.getElementById('system-toggle');
    const loadingIndicator = document.getElementById('loading');
    const templatesSection = document.getElementById('templates-section');
    const modal = document.getElementById('template-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalContent = document.getElementById('template-content');
    const closeModal = document.getElementById('close-modal');
    const useTemplateBtn = document.getElementById('use-template-btn');
    
    let currentPromptType = 'user'; // Default to user prompt
    let activeTemplate = null;
    
    // Clear button functionality
    clearBtn.addEventListener('click', function() {
        promptInput.value = '';
        promptInput.focus();
    });
    
    // Set up prompt type toggle
    userToggle.addEventListener('click', function() {
        userToggle.classList.add('active');
        systemToggle.classList.remove('active');
        currentPromptType = 'user';
        updateTemplateButtons();
    });
    
    systemToggle.addEventListener('click', function() {
        systemToggle.classList.add('active');
        userToggle.classList.remove('active');
        currentPromptType = 'system';
        updateTemplateButtons();
    });
    
    // Function to update template buttons based on prompt type
    function updateTemplateButtons() {
        // Clear existing buttons
        templatesSection.innerHTML = '';
        
        // Get the current templates based on prompt type
        const templates = currentPromptType === 'user' ? userTemplates : systemTemplates;
        
        // Create template buttons
        for (const [key, template] of Object.entries(templates)) {
            const btn = document.createElement('button');
            btn.className = 'template-btn';
            btn.textContent = template.title;
            btn.dataset.template = key;
            btn.dataset.promptType = currentPromptType;
            
            btn.addEventListener('click', function() {
                openTemplateModal(key, currentPromptType);
            });
            
            templatesSection.appendChild(btn);
        }
    }
    
    // Initialize template buttons with user templates
    updateTemplateButtons();
    
    // Modal functionality
    function openTemplateModal(templateKey, promptType) {
        activeTemplate = templateKey;
        const templates = promptType === 'user' ? userTemplates : systemTemplates;
        const template = templates[templateKey];
        
        modalTitle.textContent = template.title;
        modalContent.textContent = template.content;
        modal.style.display = 'block';
    }
    
    closeModal.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Modify use template button to append template instead of replacing
    useTemplateBtn.addEventListener('click', function() {
        if (activeTemplate) {
            const templates = currentPromptType === 'user' ? userTemplates : systemTemplates;
            const templateContent = templates[activeTemplate].content;
            
            // Get cursor position
            const cursorPosition = promptInput.selectionStart;
            const currentText = promptInput.value;
            
            // Add template at cursor position or at the end if no cursor position
            const beforeCursor = currentText.substring(0, cursorPosition);
            const afterCursor = currentText.substring(cursorPosition);
            
            // Add a double newline before the template if there's already content
            const separator = currentText && cursorPosition > 0 && !beforeCursor.endsWith('\n\n') ? 
                (beforeCursor.endsWith('\n') ? '\n' : '\n\n') : '';
            
            promptInput.value = beforeCursor + separator + templateContent + afterCursor;
            
            // Set cursor position after inserted template
            const newPosition = cursorPosition + separator.length + templateContent.length;
            promptInput.setSelectionRange(newPosition, newPosition);
            promptInput.focus();
            
            // Add highlight effect
            promptInput.classList.add('highlight-textarea');
            setTimeout(() => {
                promptInput.classList.remove('highlight-textarea');
            }, 1000);
            
            modal.style.display = 'none';
        }
    });
    
    // Enhance prompt functionality
    enhanceBtn.addEventListener('click', function() {
        const promptText = promptInput.value.trim();
        
        if (!promptText) {
            showError('Please enter a prompt to enhance.');
            return;
        }
        
        // Show loading indicator and reset output
        loadingIndicator.style.display = 'block';
        outputContent.textContent = '';
        outputContent.classList.remove('error');
        
        // Send request to the backend
        fetch('/enhance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: promptText,
                type: currentPromptType
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.error || `Server error: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            if (!data.enhanced_prompt || data.enhanced_prompt.trim() === '') {
                throw new Error('Received empty response from the server.');
            }
            
            outputContent.textContent = data.enhanced_prompt;
        })
        .catch(error => {
            console.error('Error:', error);
            showError(error.message || 'Could not enhance prompt. Please try again.');
        })
        .finally(() => {
            loadingIndicator.style.display = 'none';
        });
    });
    
    // Function to show error messages
    function showError(message) {
        outputContent.textContent = message;
        outputContent.classList.add('error');
    }
    
    // Copy button functionality
    copyBtn.addEventListener('click', function() {
        const textToCopy = outputContent.textContent;
        
        if (!textToCopy || outputContent.classList.contains('error')) {
            return;
        }
        
        navigator.clipboard.writeText(textToCopy)
            .then(() => {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                }, 2000);
            })
            .catch(err => {
                console.error('Could not copy text: ', err);
                alert('Failed to copy to clipboard. Please try again.');
            });
    });
}); 