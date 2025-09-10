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

// Image generation templates
const imageTemplates = {
    // CORE PHOTOGRAPHY TEMPLATES
    "portrait": {
        title: "Portrait Photography",
        content: `🎭 Portrait Template

Scene Type: [headshot/three-quarter/full body]
Purpose: [professional/casual/artistic/family]
Mood: [confident/approachable/serious/warm]

Subject Details:
- Age: [age range or specific]
- Gender: [gender identity]
- Ethnicity: [ethnic background]
- Build: [body type description]
- Expression: [smile/serious/contemplative/etc]
- Eye Contact: [direct/away/down/up]

Styling:
- Hair: [style/color/length]
- Makeup: [natural/professional/dramatic/none]
- Clothing: [business/casual/formal/creative]
- Accessories: [jewelry/glasses/watch/etc]

Lighting Setup:
- Type: [natural/studio/mixed]
- Direction: [front/side/back/ring]
- Quality: [soft/hard/diffused/dramatic]
- Background Separation: [yes/no/subtle]

Background:
- Type: [solid/gradient/environmental/blurred]
- Color: [specific colors or neutral]
- Texture: [smooth/textured/patterned]

Camera Settings:
- Lens: [85mm/50mm/35mm equivalent]
- Aperture: [shallow/medium/deep DOF]
- Angle: [eye level/slightly above/below]`
    },
    "landscape": {
        title: "Landscape Photography",
        content: `🏞️ Landscape Template

Scene Details:
- Location Type: [mountain/ocean/forest/urban/desert]
- Season: [spring/summer/fall/winter]
- Time: [golden hour/blue hour/midday/night]
- Weather: [clear/cloudy/stormy/misty]

Composition:
- Foreground: [rocks/flowers/water/empty]
- Midground: [trees/buildings/hills]
- Background: [mountains/sky/horizon]
- Focal Point: [specific feature to highlight]

Lighting:
- Source: [sun/moon/artificial]
- Direction: [front/side/back/overhead]
- Quality: [golden/harsh/soft/dramatic]
- Shadows: [long/short/none/dramatic]

Camera Perspective:
- View: [wide/telephoto/normal]
- Height: [ground level/elevated/aerial]
- Depth of Field: [everything sharp/selective focus]

Natural Elements:
- Water: [ocean/lake/river/waterfall/none]
- Vegetation: [lush/sparse/none/seasonal]
- Wildlife: [birds/animals/none]
- Human Elements: [buildings/people/none]`
    },
    "product": {
        title: "Product Photography",
        content: `📦 Product Template

Product Details:
- Type: [electronics/clothing/food/cosmetics/etc]
- Size: [small/medium/large]
- Material: [metal/plastic/fabric/glass/etc]
- Color Scheme: [monochrome/colorful/branded]

Setup Style:
- Approach: [clean/lifestyle/editorial/catalog]
- Background: [white/colored/textured/environmental]
- Surface: [reflective/matte/textured/floating]
- Props: [minimal/contextual/none]

Lighting Setup:
- Configuration: [key+fill/ring light/softbox/natural]
- Shadows: [none/soft/dramatic/rim]
- Reflections: [controlled/natural/minimized]

Camera Angle:
- Primary View: [front/three-quarter/side/top-down]
- Height: [eye level/above/below]
- Focus Area: [entire product/detail/feature]`
    },
    
    // STORYTELLING TEMPLATES
    "horror": {
        title: "Horror Scene",
        content: `👻 Horror Template

Atmosphere:
- Mood: [suspenseful/terrifying/eerie/psychological]
- Tension Level: [building/peak/aftermath]
- Supernatural: [yes/no/ambiguous]

Setting:
- Location: [haunted house/forest/asylum/urban decay]
- Time: [night/twilight/stormy day]
- Condition: [abandoned/deteriorating/pristine but wrong]

Subject:
- Role: [victim/investigator/entity/witness]
- Emotional State: [terrified/determined/possessed/confused]
- Physical State: [normal/injured/transformed]

Visual Elements:
- Shadows: [deep/moving/unnatural]
- Lighting: [flickering/dim/harsh contrast/colored]
- Atmosphere: [fog/smoke/none/supernatural]
- Decay: [rust/mold/cracks/overgrowth]

Horror Type:
- Style: [psychological/gore/supernatural/cosmic]
- Creatures: [none/implied/visible/abstract]
- Violence Level: [implied/moderate/intense]`
    },
    "romance": {
        title: "Romance Scene",
        content: `💕 Romance Template

Scene Type:
- Moment: [first meeting/proposal/wedding/intimate]
- Emotion: [passionate/tender/playful/dramatic]
- Relationship Stage: [new/established/rekindling]

Setting:
- Location: [beach/garden/city/home/destination]
- Ambiance: [intimate/grand/casual/luxurious]
- Time: [sunset/candlelit/morning/starry night]

Subjects:
- Count: [couple/individual/group]
- Interaction: [embracing/dancing/gazing/laughing]
- Clothing: [formal/casual/themed/seasonal]
- Chemistry: [electric/comfortable/shy/passionate]

Visual Mood:
- Color Palette: [warm/soft/vibrant/monochrome]
- Lighting: [golden/soft/romantic/dramatic]
- Effects: [bokeh/glow/sparkles/none]`
    },
    "fantasy": {
        title: "Fantasy Scene",
        content: `🧙 Fantasy Template

World Type:
- Setting: [medieval/modern urban/post-apocalyptic/otherworldly]
- Magic Level: [high/low/none/steampunk]
- Tone: [epic/dark/whimsical/gritty]

Characters:
- Type: [human/elf/dwarf/dragon/mythical creature]
- Role: [hero/villain/guide/innocent]
- Powers: [magical/enhanced/normal/cursed]
- Equipment: [sword/staff/modern/ancient artifacts]

Environment:
- Landscape: [enchanted forest/castle/floating islands/caverns]
- Architecture: [medieval/crystalline/organic/ruined]
- Weather: [magical storm/aurora/normal/supernatural]

Magical Elements:
- Effects: [glowing/sparkling/swirling/crackling]
- Creatures: [dragons/unicorns/spirits/demons]
- Artifacts: [glowing weapons/scrolls/crystals/portals]`
    },
    "scifi": {
        title: "Science Fiction",
        content: `🚀 Sci-Fi Template

Era:
- Time Period: [near future/far future/space age/cyberpunk]
- Tech Level: [advanced/experimental/alien/dystopian]
- Society: [utopian/dystopian/post-apocalyptic/space-faring]

Setting:
- Location: [space station/alien planet/megacity/laboratory]
- Environment: [sterile/industrial/organic/hybrid]
- Scale: [intimate/vast/claustrophobic/infinite]

Technology:
- Visible Tech: [holograms/robots/vehicles/weapons]
- UI Elements: [screens/displays/interfaces/none]
- Materials: [metal/energy/bio-tech/crystalline]

Characters:
- Type: [human/android/alien/cyborg]
- Equipment: [space suit/tech gear/implants/weapons]
- Role: [explorer/soldier/scientist/rebel]

Visual Style:
- Color Scheme: [neon/monochrome/natural/alien]
- Lighting: [artificial/energy-based/natural/mixed]
- Effects: [lens flares/particles/holograms/distortion]`
    },
    
    // TECHNICAL SPECIALIZED TEMPLATES
    "architectural": {
        title: "Architecture",
        content: `🏗️ Architectural Template

Building Type:
- Structure: [residential/commercial/religious/industrial]
- Style: [modern/classical/gothic/minimalist]
- Age: [new/historic/renovated/ruins]

Perspective:
- View: [exterior/interior/detail/aerial]
- Angle: [straight/dramatic/worm's eye/bird's eye]
- Focus: [whole building/section/detail/pattern]

Lighting:
- Time: [golden hour/blue hour/midday/night]
- Source: [natural/artificial/mixed]
- Mood: [dramatic/clean/moody/bright]

Composition:
- Lines: [vertical/horizontal/diagonal/curved]
- Symmetry: [perfect/near/asymmetrical]
- Framing: [full view/cropped/through elements]

Environment:
- Surroundings: [urban/rural/isolated/landscaped]
- Weather: [clear/cloudy/dramatic sky]
- People: [none/few/crowd/silhouettes]`
    },
    "vehicle": {
        title: "Vehicle Photography",
        content: `🚗 Vehicle Template

Vehicle Type:
- Category: [car/motorcycle/truck/aircraft/boat]
- Style: [classic/modern/futuristic/racing]
- Condition: [pristine/weathered/battle-damaged]

Action:
- State: [static/moving/jumping/drifting]
- Speed: [stationary/slow/fast/extreme]
- Environment: [road/track/off-road/aerial]

Camera:
- Position: [front/side/rear/three-quarter]
- Height: [ground/eye level/elevated/low]
- Movement: [static/panning/tracking]

Effects:
- Motion: [none/blur/trails/dust clouds]
- Lighting: [natural/dramatic/neon/headlights]
- Particles: [dust/smoke/sparks/water spray]

Setting:
- Location: [studio/street/highway/track/nature]
- Time: [day/night/dawn/dusk]
- Weather: [clear/rain/snow/dramatic]`
    },
    "food": {
        title: "Food Photography",
        content: `🍽️ Food Template

Dish Type:
- Category: [appetizer/main/dessert/beverage]
- Cuisine: [italian/asian/american/fusion]
- Style: [rustic/fine dining/casual/street food]

Presentation:
- Plating: [elegant/rustic/modern/traditional]
- Garnish: [minimal/elaborate/natural/artistic]
- Portion: [small/medium/large/family style]

Setup:
- Background: [clean/textured/contextual/dark]
- Props: [utensils/ingredients/napkins/none]
- Surface: [wood/marble/metal/fabric]

Lighting:
- Direction: [top/side/back/mixed]
- Quality: [soft/dramatic/natural/artificial]
- Color: [warm/neutral/cool/colored]

Angle:
- View: [overhead/45 degree/side/close-up]
- Focus: [entire dish/detail/ingredient/texture]`
    },
    "fashion": {
        title: "Fashion Photography",
        content: `👗 Fashion Template

Style Type:
- Category: [haute couture/ready-to-wear/street/editorial]
- Season: [spring/summer/fall/winter]
- Trend: [current/vintage/futuristic/timeless]

Model:
- Pose: [walking/standing/sitting/dynamic]
- Expression: [confident/serene/intense/playful]
- Interaction: [solo/group/with props]

Garments:
- Type: [dress/suit/casual/avant-garde]
- Fit: [tailored/flowing/oversized/fitted]
- Details: [textures/patterns/embellishments/minimal]

Setting:
- Location: [studio/street/nature/architecture]
- Backdrop: [seamless/textured/environmental]
- Mood: [clean/gritty/luxurious/natural]

Lighting:
- Setup: [studio/natural/mixed/dramatic]
- Mood: [bright/moody/high contrast/soft]
- Color: [neutral/warm/cool/creative]`
    },
    
    // MOOD-BASED TEMPLATES
    "vintage": {
        title: "Vintage Style",
        content: `📸 Vintage Template

Era:
- Period: [1920s/1950s/1970s/1980s/1990s]
- Style: [art deco/mid-century/disco/neon/grunge]
- Authenticity: [period accurate/inspired by/modern twist]

Visual Treatment:
- Film Type: [kodachrome/polaroid/black & white/sepia]
- Grain: [fine/heavy/none/digital]
- Color: [saturated/faded/monochrome/selective]
- Damage: [scratches/dust/light leaks/pristine]

Subject Styling:
- Clothing: [period accurate/inspired/mixed eras]
- Hair: [authentic style/modern interpretation]
- Makeup: [period correct/subtle nod/contemporary]

Setting:
- Environment: [period location/studio/modern with vintage elements]
- Props: [authentic/reproduction/modern alternatives]
- Furniture: [original/inspired/minimal]`
    },
    "minimalist": {
        title: "Minimalist Style",
        content: `⚪ Minimalist Template

Composition:
- Elements: [single subject/few objects/geometric shapes]
- Negative Space: [abundant/balanced/strategic]
- Balance: [symmetrical/asymmetrical/weighted]

Color Palette:
- Scheme: [monochrome/limited/neutral/single accent]
- Saturation: [low/medium/high/desaturated]
- Contrast: [subtle/moderate/high/none]

Subject:
- Treatment: [clean lines/simple forms/geometric]
- Detail Level: [essential only/selective/none]
- Positioning: [centered/rule of thirds/off-center]

Lighting:
- Quality: [even/soft/dramatic shadows/shadowless]
- Direction: [front/side/diffused/ambient]
- Mood: [clean/serene/stark/warm]

Background:
- Type: [solid color/gradient/texture/empty space]
- Complexity: [none/minimal/subtle pattern]`
    },
    "cinematic": {
        title: "Cinematic Style",
        content: `🎬 Cinematic Template

Genre Style:
- Type: [action/drama/thriller/romance/horror]
- Era: [classic hollywood/modern/noir/indie]
- Mood: [epic/intimate/suspenseful/uplifting]

Camera Work:
- Shot Type: [establishing/close-up/medium/master]
- Movement: [static/pan/tilt/dolly/handheld]
- Angle: [eye level/low/high/dutch/overhead]
- Lens: [wide/normal/telephoto/fisheye]

Lighting:
- Style: [three-point/natural/dramatic/soft]
- Color Temperature: [warm/cool/mixed/stylized]
- Contrast: [high/low/moderate/extreme]
- Direction: [key/fill/back/practical]

Composition:
- Framing: [tight/loose/symmetrical/dynamic]
- Depth: [shallow/deep/layered/flat]
- Leading Lines: [strong/subtle/none/multiple]

Post Processing:
- Color Grade: [teal & orange/desaturated/vibrant/monochrome]
- Film Look: [digital/film grain/vintage/clean]
- Effects: [lens flares/vignette/bloom/none]`
    },
    
    // ART STYLE TEMPLATES
    "comic": {
        title: "Comic Book Style",
        content: `💥 Comic Book Template

Art Style:
- Type: [superhero/indie/manga/webcomic]
- Era: [golden age/silver age/modern/underground]
- Line Work: [bold/fine/varied/minimal]

Color Treatment:
- Palette: [primary colors/limited/full spectrum/monochrome]
- Saturation: [high/moderate/low/selective]
- Shading: [cell shading/rendered/flat/crosshatch]
- Effects: [halftone/gradient/solid/textured]

Composition:
- Panel Style: [single image/comic panel/splash page]
- Perspective: [dramatic/normal/exaggerated/isometric]
- Action Lines: [speed/impact/motion/none]

Character Design:
- Proportions: [realistic/heroic/stylized/chibi]
- Detail Level: [high/moderate/simplified/iconic]
- Expression: [exaggerated/subtle/dramatic/stoic]`
    },
    "anime": {
        title: "Anime Style",
        content: `🎌 Anime Template

Anime Style:
- Type: [shonen/shoujo/seinen/josei/kodomomuke]
- Era: [classic/modern/retro/contemporary]
- Quality: [tv series/movie/ova/manga adaptation]

Character Design:
- Proportions: [realistic/stylized/chibi/tall & lean]
- Eyes: [large/normal/small/unique shape]
- Hair: [spiky/flowing/colorful/realistic]
- Expression: [cheerful/serious/mysterious/emotional]

Art Treatment:
- Coloring: [cell shaded/soft shaded/watercolor/digital]
- Line Weight: [varied/consistent/bold/delicate]
- Backgrounds: [detailed/simple/abstract/photographic]

Effects:
- Visual Elements: [speed lines/cherry blossoms/sparkles/auras]
- Emotional Symbols: [sweat drops/anger marks/hearts/stars]
- Lighting: [dramatic/soft/magical/realistic]`
    },
    "photorealistic": {
        title: "Photorealistic",
        content: `📷 Photorealistic Template

Realism Level:
- Target: [photograph/hyperrealistic/slightly stylized]
- Detail: [maximum/high/moderate/selective]
- Imperfections: [include/minimal/perfect/weathered]

Technical Quality:
- Resolution: [ultra high/high/standard]
- Sharpness: [tack sharp/slightly soft/selective focus]
- Noise: [none/minimal/film grain/digital noise]

Lighting:
- Accuracy: [physically accurate/enhanced/stylized]
- Complexity: [simple/complex/mixed sources]
- Shadows: [accurate/enhanced/softened]

Materials:
- Surfaces: [accurate reflections/enhanced/stylized]
- Textures: [high detail/moderate/simplified]
- Subsurface: [accurate/enhanced/simplified]

Camera Simulation:
- Lens Effects: [bokeh/chromatic aberration/distortion/clean]
- Depth of Field: [accurate/enhanced/simplified]
- Exposure: [realistic/optimized/artistic]`
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
    const imageToggle = document.getElementById('image-toggle');
    const loadingIndicator = document.getElementById('loading');
    const templatesSection = document.getElementById('templates-section');
    const modal = document.getElementById('template-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalContent = document.getElementById('template-content');
    const closeModal = document.getElementById('close-modal');
    const useTemplateBtn = document.getElementById('use-template-btn');
    
    let currentPromptType = 'user'; // Default to user prompt
    let activeTemplate = null;
    
    // Check if user is logged in by looking for logout button
    const isLoggedIn = document.querySelector('.logout-btn') !== null;
    
    // Show donation modal after login if user is logged in
    if (isLoggedIn) {
        // Check if user has already seen the donation modal this session
        if (!sessionStorage.getItem('donationModalShown')) {
            // Show donation modal with a slight delay after page load
            setTimeout(() => {
                const donationModal = document.getElementById('donation-modal');
                donationModal.style.display = 'block';
                
                // Mark as shown in this session
                sessionStorage.setItem('donationModalShown', 'true');
            }, 1000); // 1 second delay
        }
    }
    
    // Close donation modal when the close button is clicked
    document.getElementById('close-donation-modal').addEventListener('click', function() {
        document.getElementById('donation-modal').style.display = 'none';
    });
    
    // Close donation modal when "Maybe Later" button is clicked
    document.getElementById('maybe-later-btn').addEventListener('click', function() {
        document.getElementById('donation-modal').style.display = 'none';
    });
    
    // Close donation modal when clicking outside the modal content
    window.addEventListener('click', function(event) {
        const donationModal = document.getElementById('donation-modal');
        if (event.target === donationModal) {
            donationModal.style.display = 'none';
        }
    });
    
    // Helper function to clear metadata containers
    function clearMetadataContainers() {
        const existingMetadataContainers = document.querySelectorAll('.metadata-container');
        existingMetadataContainers.forEach(container => {
            container.remove();
        });
    }
    
    // Clear button functionality
    clearBtn.addEventListener('click', function() {
        promptInput.value = '';
        promptInput.focus();
        
        // Also clear the output and any metadata
        outputContent.textContent = '';
        outputContent.classList.remove('error');
        
        // Clear metadata containers
        clearMetadataContainers();
    });
    
    // Set up prompt type toggle
    userToggle.addEventListener('click', function() {
        userToggle.classList.add('active');
        systemToggle.classList.remove('active');
        imageToggle.classList.remove('active');
        currentPromptType = 'user';
        updateTemplateButtons();
    });
    
    systemToggle.addEventListener('click', function() {
        systemToggle.classList.add('active');
        userToggle.classList.remove('active');
        imageToggle.classList.remove('active');
        currentPromptType = 'system';
        updateTemplateButtons();
    });
    
    imageToggle.addEventListener('click', function() {
        imageToggle.classList.add('active');
        userToggle.classList.remove('active');
        systemToggle.classList.remove('active');
        currentPromptType = 'image';
        updateTemplateButtons();
    });
    
    // Function to update template buttons based on prompt type
    function updateTemplateButtons() {
        // Clear existing buttons
        templatesSection.innerHTML = '';
        
        // Get the current templates based on prompt type
        const templates = currentPromptType === 'user' ? userTemplates : 
                         currentPromptType === 'system' ? systemTemplates : imageTemplates;
        
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
        const templates = promptType === 'user' ? userTemplates : 
                         promptType === 'system' ? systemTemplates : imageTemplates;
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
            const templates = currentPromptType === 'user' ? userTemplates : 
                             currentPromptType === 'system' ? systemTemplates : imageTemplates;
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
        
        // Clear metadata containers
        clearMetadataContainers();
        
        // Send request to the backend
        fetch('/enhance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',  // Include credentials
            body: JSON.stringify({
                prompt: promptText,
                type: currentPromptType
            })
        })
        .then(response => {
            if (response.redirected) {
                // If we got redirected to login, reload the page
                window.location.href = response.url;
                return;
            }
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
            
            // Display the enhanced prompt
            outputContent.textContent = data.enhanced_prompt;
            
            // Add metadata display below the output
            const metadataHtml = `
                <div class="output-metadata">
                    <span>Provider: ${data.metadata.provider}</span>
                    <span>Model: ${data.metadata.model}</span>
                    <span>Time: ${data.metadata.time_taken}s</span>
                </div>
            `;
            
            // Create a container for the metadata
            const metadataContainer = document.createElement('div');
            metadataContainer.className = 'metadata-container';
            metadataContainer.innerHTML = metadataHtml;
            
            // Add the metadata after the output content
            outputContent.parentNode.insertBefore(metadataContainer, outputContent.nextSibling);
        })
        .catch(error => {
            console.error('Error:', error);
            
            // Determine if this is an API error or another type of error
            const errorMessage = error.message || 'An unknown error occurred';
            let userFriendlyMessage;
            
            if (errorMessage.includes('API request failed') || 
                errorMessage.includes('rate limit') || 
                errorMessage.includes('timeout')) {
                userFriendlyMessage = 'The enhancement service is currently experiencing high demand. Please try again in a moment.';
            } else if (errorMessage.includes('authentication') || errorMessage.includes('SESSION_LOST')) {
                userFriendlyMessage = 'Your session has expired. Please refresh the page and log in again.';
            } else {
                userFriendlyMessage = 'Could not enhance prompt. Please try again or use a different prompt.';
            }
            
            showError(`${userFriendlyMessage}<br><small>(${errorMessage})</small>`);
        })
        .finally(() => {
            loadingIndicator.style.display = 'none';
        });
    });
    
    // Function to show error messages
    function showError(message) {
        outputContent.innerHTML = message;
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