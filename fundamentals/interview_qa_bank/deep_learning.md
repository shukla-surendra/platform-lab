# Deep Learning Questions and Answers

**Q1: What is the difference between Deep Learning and Machine Learning?**

A: Machine Learning enables computers to learn from data without explicit programming and works with structured datasets, requiring manual feature engineering. Deep Learning uses multi-layered neural networks that automatically learn features from raw data, performs better on unstructured data like images and audio, and requires high computational power.

**Q2: What is a Neural Network and Artificial Neural Network (ANN)?**

A: A Neural Network is a computational model inspired by the human brain with interconnected nodes. An ANN consists of an input layer receiving raw data, hidden layers processing data through weights/biases/activation functions, and an output layer providing final predictions.

**Q3: How are Biological neurons similar to Artificial neural networks?**

A: In the human brain, neurons receive signals through dendrites, process them in the cell body, and transmit via axons. In ANNs, artificial neurons receive inputs, multiply by weights, add bias, apply activation functions, and pass output to the next layer.

**Q4: What are the different layers in a Neural Network?**

A: The input layer receives raw data, hidden layers perform computation by applying weights, biases, and activation functions to extract features progressively, and the output layer produces final results based on the task (classification uses Softmax, regression uses linear).

**Q5: What are Weights and Biases in Neural Networks?**

A: Weights are numerical values on neuron connections determining input importance. Bias is an extra parameter added to the weighted sum before activation: z = (w1*x1) + (w2*x2) + b, then an activation function is applied.

**Q6: How are weights initialized in Neural Networks?**

A: Zero initialization causes symmetry problems. Random initialization breaks symmetry but can cause gradient issues. Xavier initialization maintains balanced activations for sigmoid/tanh. He initialization suits ReLU activations. Orthogonal initialization uses random orthogonal matrices. Pretrained initialization leverages related task knowledge.

**Q7: What is an Activation Function and how does it work?**

A: An activation function decides whether a neuron activates by applying a mathematical transformation to the weighted sum plus bias. It introduces non-linearity enabling networks to learn complex patterns beyond simple linear relationships.

**Q8: What are different types of Activation Functions used in Deep Learning?**

A: Sigmoid maps inputs to 0-1 range for binary classification. Softmax converts outputs to probability distribution summing to 1. ReLU outputs 0 for negative values and input for positive values. Leaky ReLU allows small non-zero gradient for negatives. Tanh outputs between -1 and 1. ELU produces smooth negative outputs.

**Q9: Softmax vs Sigmoid — when do you use which?**

A: Sigmoid maps output to 0-1, treats outputs independently, used for binary/multi-label classification with Binary Cross-Entropy Loss. Softmax converts outputs to probability distribution summing to 1, used for multi-class classification where input belongs to exactly one class, paired with Categorical Cross-Entropy Loss.

**Q10: What is a Perceptron or Single Layer Neural Network?**

A: A perceptron is the simplest neural network for binary classification, introduced by Frank Rosenblatt in 1958. It takes multiple inputs, multiplies by weights, adds bias, applies activation function, and outputs one class if above threshold, otherwise another: y = f(sum(wi*xi) + b).

**Q11: What is Multilayer Perceptron and how is it different from Single-Layer Perceptron?**

A: Multilayer Perceptron (MLP) has hidden layers between input/output, enabling non-linear pattern learning. Each neuron connects fully to the next layer. Structure includes input layer, hidden layers processing data with weighted connections/activation functions, and output layer producing final predictions. Used for handwriting recognition and image classification.

**Q12: How are number of hidden layers and neurons per layer selected?**

A: Shallow problems use 1-2 hidden layers; complex problems use deeper networks. Universal Approximation Theorem states one hidden layer with enough neurons approximates any function, but deeper networks train more efficiently. Too few neurons cause underfitting; too many cause overfitting. Start between input/output layer sizes, adjust by validation performance.

**Q13: What is difference between Shallow Networks and Deep Networks?**

A: Shallow networks have 1-2 hidden layers, suit simple tasks, are easier to train requiring fewer computations but struggle with high-dimensional data. Deep networks have many hidden layers, learn complex hierarchical features, used for image/NLP/speech tasks, require more data/computation and techniques to avoid vanishing gradients.

**Q14: Why are Neural Networks called Black Boxes?**

A: Neural networks are called black boxes because their internal workings aren't easily interpretable. While they learn complex patterns and make accurate predictions, understanding how inputs transform to outputs is usually difficult.

**Q15: What are Feedforward Neural Networks?**

A: Feedforward Neural Networks process data in one direction only—from input through hidden layers to output. No cycles exist in connections. Each layer fully connects to the next. Training uses backpropagation with gradient descent. Works well for image recognition, speech recognition, and regression, but lacks memory of past inputs unlike recurrent networks.

**Q16: Are ANN, Single Layer Perceptron and Feedforward Neural Network the same?**

A: ANN is a broad term for any brain-inspired computational model including single/multilayer or feedforward/recurrent networks. Single Layer Perceptron is the simplest ANN with one weight layer, solves only linearly separable problems. Feedforward Neural Network is an ANN type where data flows input->hidden->output; both single and multilayer perceptrons are FNN examples.

**Q17: What are different types of Neural Networks?**

A: Feedforward Neural Networks have information flowing input-to-output with no feedback loops. Multi-Layer Perceptron is feedforward with hidden layers. Convolutional Neural Networks specialize in images using convolution/pooling layers. Recurrent Neural Networks handle sequential data maintaining hidden states. LSTM overcomes vanishing gradients using memory cells and gates. GRU simplifies LSTM with fewer gates. Autoencoders learn compressed representations. VAEs learn latent probability distributions for generation.

**Q18: What is forward and backward propagation?**

A: Forward Propagation passes input data through layers from input to output, computes weighted sums with activation functions, generates predictions, compares with actual values using loss function. Backward Propagation calculates loss gradients relative to weights using chain rule, propagates gradients backward, updates weights/biases via optimization algorithms to reduce loss.

**Q19: What is cost function in deep learning?**

A: A cost function measures difference between predicted and actual outputs, aiming for minimization so predictions approach actual results. Binary Cross-Entropy suits binary classification. Categorical Cross-Entropy handles multi-class classification. Sparse Categorical Cross-Entropy uses integer labels instead of one-hot encoding. KL Divergence measures distribution differences in generative models. Mean Squared Error applies to regression tasks.

**Q20: What is Binary Cross-Entropy, Categorical Cross-Entropy and Sparse Categorical Cross-Entropy?**

A: Binary Cross-Entropy measures predicted positive class probability versus actual label for binary classification: L = -[y*log(p) + (1-y)*log(1-p)]. Categorical Cross-Entropy compares predicted probability distribution against one-hot encoded true distribution: L = -sum(yi*log(pi)). Sparse Categorical Cross-Entropy is identical but uses integer class indices instead of one-hot encoding, saving memory for large datasets.

**Q21: How do neural networks learn from data?**

A: Networks learn through iterative forward propagation passing input through layers producing output, error calculation comparing output with target values, backpropagation computing cost function gradients relative to weights/biases using chain rule, weight/bias updates via optimization algorithms reducing error, and iteration over multiple epochs until convergence.

**Q22: What is Bias-Variance Tradeoff? What is Overfitting vs Underfitting?**

A: Bias represents error from oversimplified models; high bias means pattern capture failure. Variance represents sensitivity to training data fluctuations; high variance means noise capture. Underfitting (high bias) occurs when models are too simple, performing poorly on training/test data due to insufficient parameters or training. Overfitting (high variance) occurs when models memorize training data including noise, performing excellently on training but poorly on test data.

**Q23: What is Gradient Descent and its Variants?**

A: Gradient Descent minimizes cost functions by iteratively updating weights opposite to gradient direction. Learning rate controls step size: theta = theta - eta * dL/dtheta. Batch Gradient Descent uses entire dataset computing accurate but slow gradients. Stochastic Gradient Descent uses single samples for fast but noisy updates. Mini-Batch Gradient Descent balances both using small batches. Momentum adds previous update fractions accelerating convergence. Adaptive methods (Adagrad, RMSProp, Adam) adjust learning rates based on gradient history.

**Q24: Define learning rate in Deep Learning**

A: Learning rate is a hyperparameter controlling weight adjustment magnitude per update step. High learning rates cause unstable training or minimum skipping. Low learning rates make training stable but very slow. General update rule: w = w - eta * grad(L(w)) where eta is learning rate and grad(L(w)) is loss gradient.

**Q25: Difference between Batch Gradient Descent, Stochastic Gradient Descent and Mini-Batch Gradient Descent?**

A: Batch Gradient Descent computes gradients using entire training dataset, performs one weight update per epoch, provides stable estimates, but is slow/memory-intensive for large datasets. SGD computes gradients from single samples, updates after each sample, converges faster initially with noisy updates helping escape local minima. Mini-Batch uses small sample batches, balances stability/speed, efficiently utilizes GPU/TPU hardware, and is most commonly used in deep learning.

**Q26: Explain Adagrad, RMSProp and Adam Optimizer**

A: Adagrad adjusts learning rates per parameter based on update frequency—frequently updated parameters get smaller rates, rarely updated get larger rates. RMSProp fixes Adagrad's problem using moving average of squared gradients instead of historical sums, preventing excessive learning rate shrinkage. Adam combines momentum (exponentially decaying gradient average) with RMSProp (squared gradient average), providing fast convergence, working well for large datasets/parameters, serving as default deep learning optimizer.

**Q27: What is Momentum-based Gradient Descent?**

A: Momentum-based Gradient Descent accelerates learning by adding previous update fractions to current gradients, reducing oscillations. Formula: v = beta*v - eta*grad(L(w)), w = w + v where v is velocity, beta is momentum term (typically 0.9), eta is learning rate. Enables faster convergence especially in ravines with steep slopes in one direction and flat in another.

**Q28: What is Vanishing and Exploding Gradient Problem?**

A: During backpropagation through many layers, gradients shrink exponentially (vanishing)—earlier layers learn slowly or stop. Or gradients grow exponentially (exploding)—causing unstable weight updates and divergence. Vanishing occurs with sigmoid/tanh in deep networks. Solutions include using ReLU activations, weight initialization techniques, gradient clipping preventing explosion, and optimizers like RMSProp/Adam adapting learning rates.

**Q29: What is Gradient Clipping?**

A: Gradient Clipping prevents exploding gradients during deep neural network training. When gradients become too large, weight updates destabilize causing divergence. Norm clipping scales entire gradient vectors if norms exceed thresholds. Value clipping restricts individual gradient values to fixed ranges.

**Q30: Define Epoch, Iterations and Batches**

A: Batch is a training dataset subset used for forward/backward passes—10,000 samples with batch size 100 creates 100-sample batches. Iteration is single parameter update using one batch—10,000 samples with batch size 100 yields 100 iterations per epoch. Epoch means entire dataset processing once—with 10,000 samples and batch size 100, one epoch equals 100 iterations.

**Q31: What is difference between Parameters and Hyperparameters?**

A: Parameters are internal values learned from training data through optimization algorithms, automatically updated during training, values change throughout training—include weights/biases in neural networks. Hyperparameters are configuration settings specified before training, not learned from data, chosen through Grid Search/Random Search—include learning rate, batch size, epochs, hidden layers count, tree depth.

**Q32: How to avoid Overfitting in Neural Networks?**

A: Use more training data for better generalization. Apply L1/L2 regularization penalizing large weights. Use Dropout randomly disabling training neuron fractions, forcing robust feature learning. Apply Early Stopping terminating when validation loss plateaus. Use Data Augmentation generating new samples via transformations (rotation, flipping). Apply Batch Normalization normalizing activations. Reduce model complexity for small datasets. Use Cross-Validation monitoring validation performance.

**Q33: L1 vs L2 Regularization — how do they work?**

A: L1 Regularization (Lasso) adds absolute weight sum to loss: Loss = Original Loss + lambda*sum(|wi|), pushing some weights exactly to zero, performing feature selection by removing unimportant inputs. L2 Regularization (Ridge/Weight Decay) adds squared weight sum: Loss = Original Loss + lambda*sum(wi^2), shrinking weights toward zero rarely making them exactly zero, producing smoother more stable values than L1.

**Q34: What is Dropout and Early Stopping in Neural Networks?**

A: Dropout randomly ignores neuron fractions during training, preventing over-reliance on specific neurons, forcing robust generalized pattern learning. At test time, all neurons activate with scaled outputs matching training. Early Stopping terminates training when validation performance stops improving, preventing overfitting since continued training usually causes memorization rather than generalization.

**Q35: What is Data Augmentation and Its Techniques?**

A: Data Augmentation artificially increases training dataset size/diversity applying transformations to existing data. Image augmentation includes rotation, horizontal/vertical flips, scaling/zooming, translation/shifting, shearing, brightness/contrast adjustment, noise addition. Text augmentation includes synonym replacement, random word insertion/deletion, back translation. Time-series augmentation includes jittering, scaling, shifting, window slicing.

**Q36: What is Batch Normalization?**

A: Batch Normalization normalizes each layer's inputs producing consistent distribution during training, reducing internal covariate shift where input distribution changes as previous layers update, slowing training. Process: calculate mini-batch mean/variance, normalize inputs: x_hat = (x - mu_B)/sqrt(sigma_B^2 + eps), apply learnable scale/shift: y = gamma*x_hat + beta allowing network adjustment if needed.

**Q37: How do you evaluate a Deep Learning model?**

A: Confusion Matrix summarizes predictions versus actual labels using TP/TN/FP/FN. Accuracy measures correct prediction proportion (TP+TN)/(TP+TN+FP+FN) but misleads on imbalanced data. Precision measures actual positives among predicted positives: TP/(TP+FP), important when false positives cost high. Recall measures caught actual positives: TP/(TP+FN), important when false negatives cost high. F1-Score balances precision/recall: 2*(Precision*Recall)/(Precision+Recall). ROC-AUC plots True Positive Rate versus False Positive Rate, with AUC summarizing into 0-1 range where 1 indicates perfect separation.

**Q38: What is CNN (Convolutional Neural Network)?**

A: CNN is a deep learning model mainly for image recognition, computer vision, and pattern detection. Unlike traditional networks, CNNs automatically detect important features (edges, textures, shapes) without manual engineering. Key parts: Convolution Layer extracts features, Pooling Layer reduces dimensions via downsampling, Fully Connected Layer performs final classification. Used for image classification, face recognition, autonomous vehicles, medical imaging, NLP.

**Q39: What do you mean by Convolution?**

A: Convolution is a mathematical operation extracting features by sliding a small matrix kernel/filter over input images performing element-wise multiplication and summation. Results create feature maps highlighting important patterns (edges, corners, textures). Different filters detect different patterns—some highlight horizontal edges, others vertical edges.

**Q40: What is kernel?**

A: A kernel or filter is a small weight matrix (typically 3x3 or 5x5) sliding over inputs like images extracting features. Kernels learn automatically during training. Multiple kernels detect different features. Example 3x3 kernel with vertical edge pattern: [[1,0,-1],[1,0,-1],[1,0,-1]] highlights vertical edges as it slides over images.

**Q41: Define stride**

A: Stride is the step count the kernel moves across input matrices during convolution, deciding filter shift distance. Default stride=1 means one-cell shifts per move creating larger output feature maps. Larger strides produce smaller outputs with faster computation but less detail. Smaller strides produce bigger outputs with more detail but more computation.

**Q42: What is Pooling Layer and its different types?**

A: Pooling Layer reduces feature map sizes while preserving important information, making networks faster, preventing overfitting, capturing dominant features. Max Pooling takes maximum window values capturing important features like strong edges. Min Pooling selects minimum values, rarely used. Average Pooling takes average values keeping overall information but less effective than max pooling. Global Pooling applies across entire feature maps reducing each to single values, commonly used before fully connected layers.

**Q43: What is Receptive Field in CNN?**

A: Receptive Field is the original input image region influencing neuron outputs, defining spatial context neurons "see." First convolutional layers have receptive fields equaling kernel sizes (3x3 kernel sees 3x3 patches). Stacking layers grows receptive fields since subsequent layers aggregate wider previous-layer areas. Larger receptive fields capture global patterns recognizing whole objects; smaller receptive fields capture fine local details.

**Q44: What is Padding in CNN?**

A: Padding adds extra rows/columns (usually zeros) around input matrices before convolution, controlling spatial sizes, avoiding border information loss, allowing filters to cover edges/corners properly. Valid Padding adds nothing, output smaller than input: O = (I-K)/S + 1. Same Padding adds zeros keeping output size equal to input. Full Padding adds enough padding for kernel sliding everywhere, producing outputs larger than inputs. Reflective/Replication Padding reflects/repeats border values avoiding artificial black borders.

**Q45: What is difference between object detection and image segmentation?**

A: Object Detection identifies objects and predicts locations using bounding boxes with class labels and coordinates, not identifying exact shapes/boundaries, faster requiring less computation. Models include YOLO, Faster R-CNN, SSD, RetinaNet. Image Segmentation classifies every pixel providing exact boundaries/shapes, can be Semantic (classifying by category) or Instance (distinguishing individual same-class objects), requires more computation. Models include U-Net, Mask R-CNN, DeepLab, SegFormer.

**Q46: What are Recurrent Neural Networks (RNNs) and How it works?**

A: RNNs handle sequential data like text, speech, time series, video frames. Hidden state carries previous step information forward: h_t = f(U*h_{t-1} + W*x_t + b) where h_t is current state, x_t is input at time t, U/W are weight matrices, b is bias. Output: y_t = g(V*h_t + c). RNNs process sequentially one step at a time, update hidden states carrying memory forward, share weights across steps, and produce outputs varying by task (One-to-One/One-to-Many/Many-to-One/Many-to-Many).

**Q47: What are different types of RNN architectures?**

A: One-to-One maps single input to single output (standard feedforward). One-to-Many maps single input to output sequences—Image Captioning (one image to word sequence). Many-to-One maps input sequences to single output—Sentiment Analysis (sentence to label). Many-to-Many equal length processes aligned sequences—Part-of-Speech tagging. Many-to-Many unequal length uses Encoder-Decoder handling different sequence lengths—Machine Translation (English sentence to French).

**Q48: How does Backpropagation through time work in RNN?**

A: Backpropagation Through Time (BPTT) trains RNNs across time steps. Forward Pass: feeds input sequences step-by-step updating hidden states, producing outputs. Unrolling RNN: conceptually unfolds into feedforward network with layers per time step. Error Calculation: computes predicted/actual output differences summing across time steps for total loss. Backward Pass: uses chain rule computing loss gradients relative to weights from last to first time steps. Weight Update: optimization algorithms update weights reducing errors. Iteration: repeats over epochs accumulating gradients learning temporal dependencies.

**Q49: What is Vanishing and Exploding gradient problems in traditional RNNs?**

A: Vanishing Gradient Problem: gradients shrink exponentially during backpropagation through time, making long-term dependency learning difficult, with early time-step information having minimal weight update effects, typically caused by sigmoid/tanh squashing values between 0-1 or -1-1. Exploding Gradient Problem: gradients grow exponentially during backpropagation causing unstable training with very large weight updates, usually from large weights or long sequences. Solutions: use LSTM/GRU for vanishing gradients, apply gradient clipping for exploding gradients.

**Q50: What is LSTM and How it works?**

A: LSTM (Long Short-Term Memory) is an RNN type overcoming vanishing/exploding gradient problems, especially good at learning long-term sequential data dependencies. Unlike RNNs with single hidden states, LSTMs have memory cells retaining information controlled by gates. Cell State carries memory across time steps. Hidden State outputs each time step. Forget Gate decides previous cell state information to discard. Input Gate determines new cell state information to add. Output Gate selects current cell state information to output. Working: forget step decides what to remove, input step decides what to add, update step combines both, output step decides what to output.

**Q51: What is BiRNN and BiLSTM?**

A: BiRNN (Bidirectional RNN) processes sequences in both directions—forward (past to future) and backward (future to past), having two hidden layers per time step, capturing past and future context for better predictions, used in text classification, sentiment analysis, speech recognition. BiLSTM extends BiRNN using LSTM cells instead of standard RNN cells, processing bidirectionally while handling long-term dependencies, avoiding vanishing gradients, widely used in NLP, machine translation, named entity recognition.

**Q52: What is GRU and How it works?**

A: GRU (Gated Recurrent Unit) is an RNN type capturing long-term sequential data dependencies with simpler LSTM-like architecture. Has Update Gate (z) determining previous/new hidden state balance, Reset Gate (r) controlling previous hidden state forgetting when calculating new candidate hidden state, Candidate Hidden State computed from current input and reset-modified previous state, Final Hidden State combining previous state and candidate controlled by update gate. GRU is simpler with 2 gates versus LSTM's 3, has no separate cell state, has fewer parameters enabling faster training/lower computation, works well on smaller datasets, achieves comparable LSTM performance, easier to implement/tune.

**Q53: Difference between RNN, LSTM and GRU**

A: RNN processes sequential data maintaining hidden state carrying previous time step information, models short-term dependencies, suffers vanishing gradient problems making long-term learning difficult, has simple architecture with fewer parameters, suits short sequences and basic tasks. LSTM specialized RNN type capturing long-term dependencies using memory cells and three gates controlling information flow, effectively overcomes vanishing gradients, has more parameters requiring higher computational resources, widely used in NLP, speech recognition, time-series forecasting. GRU simplified LSTM version capturing long-term dependencies with two gates, trains faster requiring less memory, achieves similar LSTM performance, suits NLP and sequence modeling.

**Q54: What are Word Embeddings (Word2Vec, GloVe)?**

A: Before Transformer embeddings, Word Embeddings converted words to dense numerical vectors capturing semantic meaning so similar-meaning words end up close in vector space. Word2Vec (Google-developed) learns embeddings via shallow neural network trained on CBOW predicting target words from surrounding context or Skip-gram predicting surrounding context from target words, captures relationships where vector arithmetic reflects meaning—King - Man + Woman ~= Queen. GloVe (Stanford-developed) learns embeddings factorizing global word co-occurrence matrices capturing both local context windows and global dataset statistical information.

**Q55: What are Tokens and Embeddings?**

A: Tokens are basic text units models process—text split into pieces before neural network feeding. Can be words, subwords, or characters depending on tokenizer. Sentence "I love AI" yields word tokens ["I", "love", "AI"] or subword tokens ["I", "lo", "ve", "AI"]. Embeddings are token vector representations in continuous high-dimensional spaces capturing semantic meaning so similar word vectors are spatially close, allowing neural networks to process text numerically.

**Q56: What is Transformer model?**

A: Transformer is a neural network architecture relying on attention mechanisms efficiently capturing long-range sequence dependencies. Unlike traditional RNNs, processes sequences in parallel making it faster/more effective for NLP tasks—machine translation, text summarization, question answering, word embedding. Key components: Self-Attention allows each word attending to all others assigning relevance-based weights capturing short/long-term dependencies. Encoder-Decoder Architecture: Encoder processes input sequences generating context vectors, Decoder constructs output sequences step-by-step. Multi-Head Attention uses parallel attention heads learning different correlation types. Positional Encoding adds word order information. Feed-Forward Neural Networks apply position-independently. Layer Normalization/Residual Connections stabilize activations and improve gradient flow.

**Q57: What is Attention Mechanism?**

A: Attention Mechanism allows neural networks focusing on most relevant input sequence parts when predicting, captures long-range dependencies without sequential RNN processing, helps focus on important input parts, forms Transformers/BERT/GPT cores. Working: Assigning Weights—each input element receives relevance-based scores; higher scores indicate more importance. Weighted Sum—normalized scores (usually softmax) form weights computing weighted input vector sums creating context vectors. Context Vector—represents relevant information from input sequences for current output steps used for predictions.

**Q58: What are different types of attention mechanisms?**

A: Global (Soft) Attention considers all input positions computing output attention weights computing all encoder outputs weighted sums, useful capturing long-range dependencies. Local (Hard/Windowed) Attention considers input position subsets (windows around specific positions), reduces computation versus global, useful when nearby relevant context exists. Self-Attention allows sequence elements attending to same-sequence elements capturing internal relationships, Transformers core component. Scaled Dot-Product Attention computes query/key vector dot products, scales results by key dimension square roots for stability, applies softmax for attention weights. Multi-Head Attention uses parallel attention heads learning different sequence relationship types combining all head outputs for richer representations.

**Q59: What is Positional Encoding?**

A: Positional Encoding is a technique in Transformers providing token order information. Since Transformers process all input tokens in parallel unlike sequential RNNs, they lack inherent sequence order sense. Positional encoding solves this by adding position-specific information to token embeddings.

**Q60: What are Layer Normalization and Residual Connections?**

A: Layer Normalization (LayerNorm) normalizes neural network layer activations across features for each training example, ensuring outputs have mean~=0 and variance~=1, stabilizing/speeding up training, commonly used in Transformers instead of batch normalization for variable batch sizes, reduces internal covariate shift helping deeper networks converge faster. Residual Connections (Skip Connections) are shortcuts adding layer inputs directly to outputs, preserving earlier-layer information, mitigating vanishing gradients, making very deep networks trainable, improving gradient flow.

**Q61: What is Encoder-Decoder network in Deep Learning?**

A: Encoder-Decoder networks map input to output sequences having potentially different lengths/structures, used in Machine Translation, Text Summarization, Chatbots, Image Captioning. Encoder takes variable-length input sequences (sentences, images, videos) processing step-by-step creating fixed-length context vectors encoding entire sequence important information. Decoder takes encoded context vectors generating output sequences step-by-step based on context vectors and previously generated outputs. Training uses input/target sequence pairs minimizing prediction/true sequence differences via appropriate loss functions.

**Q62: BERT vs GPT — what's the difference?**

A: BERT uses only Transformer Encoder processing text bidirectionally considering left/right context of each word, pre-trained using Masked Language Modeling and Next Sentence Prediction, excels at language understanding tasks, applied to sentiment analysis, text classification, named entity recognition, question answering. GPT uses only Transformer Decoder processing text unidirectionally (left to right) predicting next tokens from previous ones, pre-trained using Causal Language Modeling, excels at generating coherent context-aware text, applied to chatbots, text generation, summarization, code generation, content creation.

**Q63: What is Autoencoder?**

A: Autoencoder is a neural network learning efficient data representations by training to reconstruct input at output, commonly used for dimensionality reduction, feature learning, anomaly detection, data denoising, unsupervised models requiring no labeled data, trained reproducing inputs as accurately as possible. Key components: Encoder compresses input data into lower-dimensional latent representations (bottlenecks) capturing important features while reducing redundancy. Latent Space holds compressed representations containing input reconstruction essential information. Decoder reconstructs original input from latent representations minimizing difference between input/output via losses like Mean Squared Error.

**Q64: What are different types of Autoencoder?**

A: Vanilla (Basic) Autoencoder has encoder/decoder learning compressed latent representations, mainly for dimensionality reduction/feature learning. Denoising Autoencoder trained reconstructing original input from corrupted/noisy versions, learning robust noise-insensitive features, useful for image/signal denoising. Sparse Autoencoder adds sparsity constraints to latent representations encouraging neuron inactivity forcing efficient meaningful feature learning. Variational Autoencoder (VAE) probabilistic autoencoder modeling latent space as probability distributions, generating new samples via sampling, widely used for image generation. Convolutional Autoencoder uses convolutional layers instead of fully connected, better for images/spatial data preserving spatial hierarchies. Contractive Autoencoder adds regularization terms making latent representations robust to small input changes learning invariant features.

**Q65: What is Variational Autoencoder (VAE)?**

A: Variational Autoencoder (VAE) is a probabilistic autoencoder learning underlying input data probability distributions. Unlike standard autoencoders mapping inputs to fixed latent vectors, VAEs map inputs to latent space distributions allowing new realistic data sample generation.

**Q66: Autoencoder vs PCA — how do they differ?**

A: PCA (Principal Component Analysis) is linear dimensionality reduction transforming data into principal components capturing maximum variance, requires no neural network training, computationally efficient and easily interpretable, works best with linear data relationships. Autoencoder is unsupervised neural network learning compressed representations via encoder/decoder, learns non-linear relationships, requires training and higher computational resources than PCA, widely used for dimensionality reduction, denoising, anomaly detection, feature learning.

**Q67: What is Seq2Seq Model?**

A: Sequence-to-Sequence (Seq2Seq) models map input sequences to output sequences with potentially different lengths. Key components: Encoder processes input sequences compressing into fixed-length context vectors encoding entire input essential information. Decoder generates output sequences step-by-step using context vectors. Attention Mechanism (common but optional) allows decoders focusing on relevant input sequence parts each step instead of depending solely on fixed context vectors improving especially long sequence performance.

**Q68: What is Generative Adversarial Network (GAN)?**

A: GAN is a neural network architecture generating realistic data resembling given datasets consisting of Generator and Discriminator. Generator takes random noise vectors generating synthetic data (images, text, audio) aiming to fool discriminators thinking generated data is real. Discriminator takes real/generated data predicting reality versus fakeness, correctly distinguishing training set real data from generator fake data. Working: Generator creates fake samples, Discriminator evaluates against real data, both networks update weights based on performances training simultaneously.

**Q69: Different types of Generative Adversarial Networks (GANs)?**

A: Vanilla GAN has simple generator/discriminator training on adversarial losses generating realistic data from random noise. Conditional GAN (cGAN) generates data conditioned on additional information like class labels generating specific digit/object categories. Deep Convolutional GAN (DCGAN) uses convolutional layers in generator/discriminator better for images capturing spatial hierarchies. Wasserstein GAN (WGAN) uses Wasserstein distance instead of standard losses stabilizing training reducing mode collapse. Least Squares GAN (LSGAN) uses least squares discriminator loss instead of cross-entropy producing higher quality images. CycleGAN enables image-to-image translation without paired datasets—horses to zebras, summer to winter. Progressive GAN (PGGAN) progressively trains from low to high resolution producing high-quality outputs. StyleGAN introduces style-based generator architecture allowing generated image feature control.

**Q70: What is Mode Collapse and why is GAN training unstable?**

A: Mode Collapse occurs when Generator learns producing only limited output varieties (or single output) reliably fooling Discriminators instead of learning full real data distribution diversity. GAN training is unstable because: Adversarial dynamics—Generator/Discriminator optimize against each other in minimax games rather than toward shared objectives, improvements in one destabilize another. Vanishing gradients—Too-good Discriminators give Generator little useful gradient signals stalling training. No guaranteed convergence—Networks may oscillate indefinitely instead of stable equilibria. Hyperparameter sensitivity—Learning rates, architecture balance, loss function choices significantly affect stability.

**Q71: What is StyleGAN?**

A: StyleGAN is a GAN type designed for high-quality image generation with fine-grained feature control developed by NVIDIA producing photorealistic human faces/other high-resolution images. Style-Based Generator transforms latent vectors into "styles" at each layer enabling different detail control: coarse features (pose, shape), middle features (facial features), fine features (hair, skin texture). Adaptive Instance Normalization (AdaIN) combines latent styles with layer feature maps enabling separate attribute manipulation. Separation of Features allows coarse, middle, fine features independent manipulation giving better generated image control. High-Resolution Image Generation produces very realistic detailed images compared to traditional GANs avoiding typical artifacts.

**Q72: What is Transfer Learning?**

A: Transfer Learning is a deep learning technique reusing pre-trained models on large datasets for new related tasks. Instead of training from scratch, it uses original task knowledge. Example: using ImageNet-trained CNNs for medical image classification. Process: take ImageNet pre-trained CNN, freeze first convolutional layers, retrain last layers on new task datasets.

**Q73: What is Difference Between Transfer Learning and Fine-Tuning?**

A: Transfer Learning reuses pre-trained model knowledge for new tasks, freezes most/all pre-trained layers, trains only final classification/output layers, requires less training time/computational resources, works well with small datasets. Fine-Tuning starts with pre-trained models continuing training on new datasets, unfreezes some/all pre-trained layers updating them, adapts learned features to target tasks, requires more training time/computational resources than transfer learning, achieves better performance with sufficient task-specific data.
