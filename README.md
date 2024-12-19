# PetMagix - AI-Powered Pet Care Assistant

PetMagix is an intelligent pet care platform that combines AI technology with veterinary expertise to provide 24/7 pet health support. Using X.AI's Grok models, it offers both text-based consultations and image analysis for comprehensive pet care.

## Features

- 🤖 AI Veterinary Assistant (VetX)
- 📸 Image Analysis for Pet Health Issues
- 🐾 Pet Profile Management
- 💬 Real-time Chat Interface
- 📱 Mobile-Responsive Design
- 🔒 Secure User Authentication
- 📊 Health History Tracking

## Live Demo

Visit [PetMagix on Render](https://petmagix.onrender.com) to try it out!

## Deployment Instructions

### Deploy to Render

1. Fork this repository
2. Create a free account on [Render](https://render.com)
3. Click "New +" and select "Blueprint"
4. Connect your GitHub account and select this repository
5. Render will automatically configure both the web service and PostgreSQL database
6. Add your X.AI API key in the environment variables:
   - Key: `XAI_API_KEY`
   - Value: Your X.AI API key

The deployment will automatically:
- Create a PostgreSQL database
- Set up the web service
- Configure environment variables
- Handle SSL certification

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/petmagix.git
cd petmagix
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a .env file:
```
XAI_API_KEY=your_xai_api_key
SECRET_KEY=your_secret_key
```

5. Run the application:
```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## Technology Stack

- **Backend**: Python, Flask
- **Database**: PostgreSQL (Production), SQLite (Development)
- **AI Models**: 
  - grok-beta (Text Processing)
  - grok-2-vision-1212 (Image Analysis)
- **Frontend**: HTML5, CSS3, JavaScript
- **Deployment**: Render.com

## Project Structure

```
petmagix/
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── schema.sql         # SQLite schema
├── schema_postgres.sql # PostgreSQL schema
├── render.yaml        # Render deployment config
├── static/
│   ├── css/          # Stylesheets
│   ├── images/       # Static images
│   ├── js/          # JavaScript files
│   └── uploads/      # User uploaded images
└── templates/
    ├── auth/         # Authentication templates
    ├── chat/         # Chat interface templates
    ├── dashboard/    # Dashboard templates
    └── profile/      # Pet profile templates
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, email support@petmagix.com or open an issue in this repository.
