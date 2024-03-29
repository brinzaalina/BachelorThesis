import { DefaultButton, TextField } from "@fluentui/react";
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Journal } from "../../models/journal";
import { addJournal } from "../../services/api-service";
import { addContentInputStyle, addInputClassName, addJournalClassName, addJournalTitleClassName, addTitleInputStyle, buttonsClassName, cancelButtonClassName, saveButtonClassName } from "./add-journal-page-style";

export const AddJournalPage = () => {
    const navigate = useNavigate();
    const [title, setTitle] = useState<string>('');
    const [content, setContent] = useState<string>('');
    const [titleError, setTitleError] = useState<string>('');
    const [contentError, setContentError] = useState<string>('');
    const token = localStorage.getItem("token");

    const handleSave = () => {
        const journal: Journal = {
          entry_title: title,
          entry_text: content,
        };
        if (title === '' || title.length < 4) {
            setTitleError('Title too short!');
            return;
        } else if (content === '' || content.length < 4) {
            setContentError('Content too short!');
            return;
        }
        addJournal(token!, journal).then((response) => {
            navigate('/patient');
        }).catch((error) => {
            console.log(error);
            alert(error);
        });
    };


    const onChangeTitle = React.useCallback(
        (event: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
          setTitle(newValue!);
        },
        [],
    );

    const onChangeContent = React.useCallback(
        (event: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
            setContent(newValue!);
        },
        [],
    );

    const handleCancel = () => {
        setTitle('');
        setContent('');
        navigate('/patient');
    };

    if (token) {
        if (localStorage.getItem('userType') !== 'patient') {
          if (localStorage.getItem("userType") === "therapist") {
            navigate("/therapist");
          } else {
            navigate("/login");
          }
        }
    } else {
        navigate('/login');
    }

    return (
      <div className={addJournalClassName}>
        <h2 className={addJournalTitleClassName}>Add a journal</h2>
        <TextField
          className={addInputClassName}
          label="Title"
          value={title}
          onChange={onChangeTitle}
          errorMessage={titleError}
          styles={addTitleInputStyle}
        />
        <TextField
          className={addInputClassName}
          label="Content"
          multiline
          rows={10}
          value={content}
          onChange={onChangeContent}
          errorMessage={contentError}
          styles={addContentInputStyle}
        />
        <div className={buttonsClassName}>
          <DefaultButton
            className={saveButtonClassName}
            text="Save"
            onClick={handleSave}
          />
          <DefaultButton
            className={cancelButtonClassName}
            text="Cancel"
            onClick={handleCancel}
          />
        </div>
      </div>
    );
};