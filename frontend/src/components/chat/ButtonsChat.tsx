import React, { useState, useRef } from 'react';
import { FaPlus, FaImage, FaBriefcase, FaPaperPlane } from 'react-icons/fa';
import '@/styles/animations/ProffesionToggle.css';
import FileAttachment from './FileAttachment';
import { ChatMessageType } from '@/types/ChatMessageType';
import { useUser } from '@/contexts/UserContext';
import { useChat } from '@/contexts/chat/ChatContext';
import { GetSuggestions } from '@/services/api';
import { useSuggestions } from '@/contexts/chat/SuggestionsContext';

interface ButtonsChatProps{
    isProfessionOpen: boolean;
    setIsProfessionOpen: (isOpen: boolean) => void;
}

const ButtonsChat: React.FC<ButtonsChatProps> = ({ isProfessionOpen, setIsProfessionOpen }) => {
    const [profession, setProfession] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);
    const { selectedFiles, setSelectedFiles, handleChatSubmit, fetchSubTasks } = useChat();
    const { suggestions, setSuggestions } = useSuggestions();
    const { user, setUser } = useUser();

    const handleImageClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(event.target.files || []);
        if (files.length > 0) {
            setSelectedFiles([...selectedFiles, ...files]);
        }
    };

    const handleProfessionSubmit = async (e: React.MouseEvent) => {
        e.preventDefault();
        if (profession.trim()) {
            try {
                const newSuggestions = await GetSuggestions(profession);
                setSuggestions(newSuggestions);
                setProfession('');
            } catch (error) {
                console.error('Error fetching suggestions:', error);
            }
        }
    };

    const handleKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleProfessionSubmit(e as any);
        }
    };

    return (
        <div className="flex gap-4 mx-4 my-4 items-center">
            <button className="w-10 h-10 rounded-full bg-white border-2 border-gray-300 
                             flex items-center justify-center text-gray-500
                             hover:bg-gray-100 hover:border-gray-400 hover:text-gray-700 
                             transition-all duration-200">
                <FaPlus className="w-5 h-5" />
            </button>

            <input 
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="*"
                multiple
                className="hidden"
            />

            <button 
                className={`w-10 h-10 rounded-full bg-white border-2 
                           flex items-center justify-center
                           transition-all duration-200
                           ${selectedFiles.length > 0
                             ? 'border-green-500 text-green-500 hover:bg-green-50' 
                             : 'border-gray-300 text-gray-500 hover:bg-gray-100 hover:border-gray-400 hover:text-gray-700'
                           }`}
                onClick={handleImageClick}
                title={selectedFiles.length > 0 ? `${selectedFiles.length} files selected` : 'Select images'}
            >
                <FaImage className="w-5 h-5" />
            </button>

            <div className={`profession-viewport ${isProfessionOpen ? 'open' : ''}`}>
                <div className="profession-content">
                    <button 
                        className="w-10 h-10 rounded-full bg-white border-2 border-gray-300 
                                 flex items-center justify-center text-gray-500
                                 hover:bg-gray-100 hover:border-gray-400 hover:text-gray-700 
                                 transition-all duration-200 shrink-0"
                        onClick={() => setIsProfessionOpen(!isProfessionOpen)}
                    >
                        <FaBriefcase className="w-5 h-5" />
                    </button>
                    <input 
                        value={profession}
                        onChange={(e) => setProfession(e.target.value)}
                        onKeyDown={handleKeyDown}
                        className="h-8 w-36 px-3 rounded-full bg-transparent border border-gray-300 
                                 text-sm placeholder:text-gray-500 focus:outline-none 
                                 focus:border-gray-400 focus:ring-1 focus:ring-gray-400
                                 transition-all shadow-sm"
                        placeholder="Enter profession..."
                    />
                    <button 
                        onClick={handleProfessionSubmit}
                        className="h-8 px-4 rounded-full bg-green-400 text-white text-sm font-medium
                                 hover:bg-green-500 active:bg-green-700 
                                 transition-colors duration-200 shrink-0
                                 shadow-sm flex items-center justify-center"
                    >
                        Get Tasks
                    </button>
                </div>
            </div>

            <div className="ml-auto">
                <button 
                    className={`w-10 h-10 rounded-full
                               flex items-center justify-center
                               transition-all duration-200
                               ${selectedFiles.length > 0
                                 ? 'text-green-500 hover:text-green-600' 
                                 : 'text-gray-500 hover:text-gray-700'
                               }`}
                    onClick={() => {
                        fetchSubTasks();
                        handleChatSubmit();
                    }}
                >
                    <FaPaperPlane className="w-5 h-5" />
                </button>
            </div>
        </div>
    );
}

export default ButtonsChat;