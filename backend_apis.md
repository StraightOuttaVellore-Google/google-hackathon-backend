## **App Details:**
### Study Mode:

1. Pomodoro Timer  
2. Color Noises (White Noise, Brown Noise, Pink Noise, etc\>)  
3. Eisenhower Priority Matrix based TODO List maintainer  
4. Blocking Mode: It is a full screen mode with an animated cat that keeps getting fish as long as you focus. Clicking escape key helps you come out of this mode  
5. Chatbot box: This chatbot acts as a personal assistant to help people organize and manage their days

### Wellness Mode

1. AI Voice Agent for journaling  
2. Pathways for the user to improve their mental wellness  
3. Moodboard for the user to have a recap of their mood  
4. World: A twitter like place for people to share their addiction overcoming or illness overcoming achievements  
5. Community: A place for people to chat in groups with one another

## **HTTP API Endpoints**

1.  **`GET: /user/{user_id}`**

      * **Description**: This is the first call made to get all the data required to set the application's initial state.
      * **Output**:
        ```json
        {
          "user_id": "",
          "startup_data": "StartupData"
        }
        ```

2.  **`POST: /study/eisenhower`**

      * **Description**: This is used to add a task to the Eisenhower Priority Matrix.
      * **Input**:
        ```json
        {
          "user_id": "",
          "task_id": "",
          "task_title": "",
          "task_description": "",
          "task_quadrant": ""
        }
        ```

3.  **`GET: /study/chatbot`**

      * **Description**: Used for interacting with the chatbot.
      * **Input**:
        ```json
        {
          "user_id": "",
          "chat_id": "",
          "query": [
            { "role": "", "text": "" },
            ...
          ]
        }
        ```
      * **Output**:
        ```json
        {
          "chat_id": "",
          "response": ""
        }
        ```

4.  **`POST: /study/growth`**

      * **Description**: Sends to the server how many "fishes" were earned.
      * **Input**:
        ```json
        {
          "user_id": "",
          "seconds_used": "",
          "target": "",
          "fishes_earned": ""
        }
        ```

5.  **`GET: /wellness/mood_summary`**

      * **Description**: Called when a user clicks on a particular day on the mood board.
      * **Input**: `?date="..."`
      * **Output**:
        ```json
        {
          "title": "",
          "summary": "",
          "tags": "",
          "emoji": "😊"
        }
        ```

6.  **`POST: /wellness/summary-journal`**

      * **Description**: After a user has finished journaling, this data is post-processed and sent to update the server.
      * **Input**:
        ```json
        {
          "title": "",
          "audio_transcript": "",
          "audio_conversation": ".wav",
          "summary": "",
          "remarks": "",
          "mood_tags": [],
          "risk_assessment": ""
        }
        ```

7.  **`GET: /wellness/pathways_list`**

      * **Description**: Returns a list of pathways and information about them.
      * **Output**:
        ```json
        {
          "list_of_pathways": "[Pathway]"
        }
        ```

8.  **`GET: /wellness/pathways/{path_id}/{node_no}`**

      * **Description**: Called when a user clicks on a node in a pathway. The data is displayed in a pop-up with a 'start-exercise' button containing a hyperlink to a game/exercise.
      * **Output**:
        ```json
        {
          "title": "",
          "description": "",
          "link_to_game": ""
        }
        ```

-----

### **Websocket APIs**

1.  `/wellness/voice_agent`
2.  `/wellness/community`
3.  `/wellness/world`